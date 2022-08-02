import hashlib
import importlib
import logging
import requests
import urllib
from base64 import b16decode, b16encode
from collections import OrderedDict
from Crypto.Cipher import Blowfish
from Crypto.Hash import HMAC, SHA256
from Crypto.Util import Padding
from decimal import Decimal
from django import forms
from django.conf import settings
from django.http import HttpRequest
from django.template.loader import get_template
from django.utils.safestring import mark_safe
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from pretix.base.decimal import round_decimal
from pretix.base.forms import SecretKeySettingsField
from pretix.base.models import Event, Order, OrderPayment, OrderRefund
from pretix.base.payment import BasePaymentProvider, PaymentException
from pretix.base.settings import SettingsSandbox
from pretix.multidomain.urlreverse import build_absolute_uri
from urllib.parse import parse_qsl, urlencode

logger = logging.getLogger("pretix_computop")


class ComputopSettingsHolder(BasePaymentProvider):
    identifier = "computop_settings"
    verbose_name = _("Computop")
    is_enabled = False
    is_meta = True
    payment_methods_settingsholder = []

    def __init__(self, event: Event):
        super().__init__(event)
        self.settings = SettingsSandbox("payment", self.identifier.split("_")[0], event)

    @property
    def settings_form_fields(self):
        fields = [
            (
                "merchant_id",
                forms.CharField(
                    label=_("Merchant ID"),
                    help_text=_("as sent to you by mail from your payment provider"),
                    validators=(),
                ),
            ),
            (
                "blowfish_password",
                SecretKeySettingsField(
                    label=_("Encryption key"),
                    help_text=_("also called Blowfish-password, as sent to you by mail from your payment provider"),
                    validators=(),
                ),
            ),
            (
                "hmac_password",
                SecretKeySettingsField(
                    label=_("HMAC key"),
                    help_text=_("as sent to you by mail from your payment provider"),
                    validators=(),
                ),
            ),
        ]

        d = OrderedDict(
            fields
            + self.payment_methods_settingsholder
            + list(super().settings_form_fields.items())
        )
        d.move_to_end("_enabled", last=False)
        return d


class ComputopMethod(BasePaymentProvider):
    identifier = ""
    method = ""
    verbose_name = ""
    apiurl = "https://www.computop-paygate.com/paymentpage.aspx"

    def __init__(self, event: Event):
        super().__init__(event)
        self.settings = SettingsSandbox("payment", self.identifier.split("_")[0], event)

    @property
    def settings_form_fields(self):
        return {}

    @property
    def is_enabled(self) -> bool:
        if self.type == "meta":
            module = importlib.import_module(
                __name__.replace("computop", self.identifier.split("_")[0]).replace(
                    ".payment", ".paymentmethods"
                )
            )
            for method in list(
                filter(
                    lambda d: d["type"] in ["meta", "scheme"], module.payment_methods
                )
            ):
                if self.settings.get("_enabled", as_type=bool) and self.settings.get(
                    "method_{}".format(method["method"]), as_type=bool
                ):
                    return True
            return False
        else:
            return self.settings.get("_enabled", as_type=bool) and self.settings.get(
                "method_{}".format(self.method), as_type=bool
            )

    def is_allowed(self, request: HttpRequest, total: Decimal) -> bool:
        return super().is_allowed(request, total) and self._decimal_to_int(total) >= 100

    def payment_form_render(
        self, request: HttpRequest, total: Decimal, order: Order = None
    ) -> str:
        template = get_template("pretix_computop/checkout_payment_form.html")
        return template.render()

    def checkout_prepare(self, request, cart):
        return True

    def payment_is_valid_session(self, request):
        return True

    def checkout_confirm_render(self, request, order: Order = None) -> str:
        template = get_template("pretix_computop/checkout_payment_confirm.html")
        ctx = {"request": request}
        return template.render(ctx)

    def test_mode_message(self) -> str:
        return mark_safe(
            _(
                "The {ident} plugin is operating in test mode. You can use one of <a {cardargs}>many test "
                "cards</a> to perform a transaction. No money will actually be transferred."
            ).format(
                ident=self.verbose_name,
                cardargs='href="https://developer.computop.com/pages/viewpage.action?pageId=26247897" '
                'target="_blank"',
            )
        )

    def execute_payment(self, request: HttpRequest, payment: OrderPayment) -> str:
        data = self._get_payment_data(payment)
        encrypted_data = self._encrypt(urlencode(data, safe=":/"))
        payload = {
            "MerchantID": self.settings.get("merchant_id"),
            "Len": encrypted_data[1],
            "Data": encrypted_data[0],
            "Language": payment.order.locale[:2],
        }
        data["Description"] = "Payment process initiated but not completed"
        payment.info_data = data
        payment.save(update_fields=["info"])
        return self.apiurl + "?" + urlencode(payload, safe="|")

    def api_payment_details(self, payment: OrderPayment):
        return {
            "id": payment.info_data.get("PayID", None),
            "payment_method": payment.info_data.get("pt", None),
        }

    def matching_id(self, payment: OrderPayment):
        return payment.info_data.get("PayID", None)

    def payment_control_render(
        self, request: HttpRequest, payment: OrderPayment
    ) -> str:
        template = get_template("pretix_computop/control.html")
        ctx = {
            "request": request,
            "event": self.event,
            "settings": self.settings,
            "payment_info": payment.info_data,
            "payment": payment,
            "method": self.method,
            "provider": self,
        }
        return template.render(ctx)

    def payment_control_render_short(self, payment: OrderPayment) -> str:
        payment_info = payment.info_data
        r = payment_info.get("PayID", "")
        if payment_info.get("pt"):
            if r:
                r += " / "
            r += payment_info.get("pt")
        if payment_info.get("CCBrand"):
            if r:
                r += " / "
            r += payment_info.get("CCBrand")
        return r

    def payment_refund_supported(self, payment: OrderPayment) -> bool:
        if "PayID" in payment.info:
            return True
        return False

    def payment_partial_refund_supported(self, payment: OrderPayment) -> bool:
        if "PayID" in payment.info:
            return True
        return False

    def execute_refund(self, refund: OrderRefund):
        data = self._get_refund_data(refund)

        encrypted_data = self._encrypt(urlencode(data))
        payload = {
            "MerchantID": self.settings.get("merchant_id"),
            "Len": encrypted_data[1],
            "Data": encrypted_data[0],
        }

        req = requests.post(
            "https://www.computop-paygate.com/credit.aspx",
            data=payload,
        )

        parsed = urllib.parse.parse_qs(req.text)
        processed = self.parse_data(parsed["Data"][0])
        self.process_result(refund, processed)

    def refund_control_render(self, request: HttpRequest, refund: OrderRefund) -> str:
        return self.payment_control_render(request, refund)

    def check_hash(self, payload_parsed):
        mid = payload_parsed["mid"]
        mac = str(payload_parsed["MAC"]).rstrip()
        trans_id = payload_parsed["TransID"]
        pay_id = payload_parsed["PayID"]
        status = payload_parsed["Status"]
        code = payload_parsed["Code"]
        if mid == self.settings.get("merchant_id") and mac == self._calculate_hmac(
            pay_id, trans_id, status, code
        ):
            return True
        else:
            return False

    def parse_data(self, data):
        payload = self._decrypt(str(data))
        return dict(parse_qsl(payload))

    def process_result(self, payment_or_refund, data, datasource=None):
        if datasource:
            payment_or_refund.order.log_action(
                "pretix_computop.event", data={"source": datasource, "data": data}
            )

        if isinstance(payment_or_refund, OrderPayment):
            payment = payment_or_refund

            # OK
            if data["Code"][:1] == "0":
                if payment.state not in (
                    OrderPayment.PAYMENT_STATE_CONFIRMED,
                    OrderPayment.PAYMENT_STATE_REFUNDED,
                ):
                    payment.info_data = data
                    payment.save(update_fields=["info"])
                    payment.confirm()
            # Error || Fatal Error
            elif data["Code"][:1] in ["2", "4"]:
                if payment.state not in (
                    OrderPayment.PAYMENT_STATE_CONFIRMED,
                    OrderPayment.PAYMENT_STATE_REFUNDED,
                ):
                    payment.fail(info=data)
            # Continue / Transient || EMV 3DS Info
            elif data["Code"][:1] in ["6", "7"]:
                if payment.state == OrderPayment.PAYMENT_STATE_CREATED:
                    payment.state = OrderPayment.PAYMENT_STATE_PENDING
                    payment.info_data = data
                    payment.save(update_fields=["state", "info"])
            else:
                payment.fail(info=data)

        elif isinstance(payment_or_refund, OrderRefund) and payment_or_refund.state in (
            OrderRefund.REFUND_STATE_CREATED,
            OrderRefund.REFUND_STATE_TRANSIT,
        ):
            refund = payment_or_refund

            # OK
            if data["Code"][:1] == "0":
                refund.info_data = data
                refund.save(update_fields=["info"])
                refund.done()
            # Error || Fatal Error
            elif data["Code"][:1] in ["2", "4"]:
                refund.state = OrderRefund.REFUND_STATE_FAILED
                refund.execution_date = now()
                refund.info_data = data
                refund.save(update_fields=["state", "execution_date", "info"])
            # Continue / Transient || EMV 3DS Info
            elif data["Code"][:1] in ["6", "7"]:
                refund.state = OrderRefund.REFUND_STATE_TRANSIT
                refund.info_data = data
                refund.save(update_fields=["state", "info"])
            else:
                refund.state = OrderRefund.REFUND_STATE_FAILED
                refund.execution_date = now()
                refund.info_data = data
                refund.save(update_fields=["state", "execution_date", "info"])
        else:
            raise PaymentException(_("We had trouble processing your transaction."))

    def _encrypt(self, plaintext):
        key = self.settings.get("blowfish_password").encode("UTF-8")
        cipher = Blowfish.new(key, Blowfish.MODE_ECB)
        bs = Blowfish.block_size
        padded_text = Padding.pad(plaintext.encode("UTF-8"), bs)
        encrypted_text = cipher.encrypt(padded_text)
        return b16encode(encrypted_text).decode(), len(plaintext)

    def _decrypt(self, ciphertext):
        key = self.settings.get("blowfish_password").encode("UTF-8")
        cipher = Blowfish.new(key, Blowfish.MODE_ECB)
        bs = Blowfish.block_size
        ciphertext_bytes = b16decode(ciphertext)
        try:
            decrypted_text = cipher.decrypt(ciphertext_bytes)
        except (TypeError, ValueError) as e:
            logger.exception(e)
            raise PaymentException(
                _(
                    "We had trouble communicating with the payment service. Please try again and get "
                    "in touch with us if this problem persists."
                )
            )
        try:
            unpadded_text = Padding.unpad(decrypted_text, bs)
        except ValueError:
            unpadded_text = (
                decrypted_text.rstrip()
            )  # sometimes bs and padding are wrong, we strip ending spaces then
        return unpadded_text.decode("UTF-8")

    def _calculate_hmac(
        self, payment_id="", transaction_id="", amount_or_status="", currency_or_code=""
    ):
        merchant_id = self.settings.get("merchant_id")
        cat = "*".join(
            [
                payment_id,
                transaction_id,
                merchant_id,
                amount_or_status,
                currency_or_code,
            ]
        )
        plain = cat.encode("UTF-8")
        secret = self.settings.get("hmac_password").encode("UTF-8")
        h = HMAC.new(secret, digestmod=SHA256)
        h.update(plain)
        return h.hexdigest().upper()

    def _amount_to_decimal(self, cents):
        places = settings.CURRENCY_PLACES.get(self.event.currency, 2)
        return round_decimal(float(cents) / (10**places), self.event.currency)

    def _decimal_to_int(self, amount):
        places = settings.CURRENCY_PLACES.get(self.event.currency, 2)
        return int(amount * 10**places)

    def _get_payment_data(self, payment: OrderPayment):
        ident = self.identifier.split("_")[0]
        trans_id = payment.full_id
        ref_nr = payment.full_id
        return_url = build_absolute_uri(
            self.event,
            "plugins:pretix_{}:return".format(ident),
            kwargs={
                "order": payment.order.code,
                "hash": hashlib.sha1(payment.order.secret.lower().encode()).hexdigest(),
                "payment": payment.pk,
                "payment_provider": ident,
            },
        )
        notify_url = build_absolute_uri(
            self.event,
            "plugins:pretix_{}:notify".format(ident),
            kwargs={
                "order": payment.order.code,
                "hash": hashlib.sha1(payment.order.secret.lower().encode()).hexdigest(),
                "payment": payment.pk,
                "payment_provider": ident,
            },
        )
        data = {
            "MerchantID": self.settings.get("merchant_id"),
            "TransID": trans_id,
            "OrderDesc": "{}Order {}-{}".format(
                "Test:0000 " if payment.order.testmode else "",
                self.event.slug.upper(),
                payment.full_id,
            ),
            "RefNr": ref_nr,
            "Amount": self._decimal_to_int(payment.amount),
            "Currency": self.event.currency,
            "URLSuccess": return_url,
            "URLFailure": return_url,
            "URLNotify": notify_url,
            "URLBack": return_url,
            "MAC": self._calculate_hmac(
                transaction_id=trans_id,
                amount_or_status=str(self._decimal_to_int(payment.amount)),
                currency_or_code=self.event.currency,
            ),
            "Response": "encrypt",
        }
        return data

    def _get_refund_data(self, refund: OrderRefund):
        data = {
            "MerchantID": self.settings.get("merchant_id"),
            "Amount": self._decimal_to_int(refund.amount),
            "Currency": self.event.currency,
            "MAC": self._calculate_hmac(
                payment_id=refund.payment.info_data["PayID"],
                transaction_id=refund.full_id,
                amount_or_status=str(self._decimal_to_int(refund.amount)),
                currency_or_code=self.event.currency,
            ),
            "PayID": refund.payment.info_data["PayID"],
            "TransID": refund.full_id,
        }
        return data


class ComputopEDD(ComputopMethod):
    apiurl = "https://www.computop-paygate.com/paysdd.aspx"
    extra_form_fields = []

    def _get_payment_data(self, payment: OrderPayment):
        data = super()._get_payment_data(payment)
        data["OrderDesc2"] = ""
        data["MandateID"] = payment.full_id
        data["DtOfSgntr"] = payment.created.strftime("%d.%m.%Y")
        return data

    def get_refund_data(self, refund: OrderRefund):
        data = super()._get_refund_data(refund)
        data["RefNr"] = refund.full_id  # not for EVO
        return data


class ComputopCC(ComputopMethod):
    apiurl = "https://www.computop-paygate.com/payssl.aspx"
    extra_form_fields = []

    def _get_payment_data(self, payment: OrderPayment):
        data = super()._get_payment_data(payment)
        data["msgver"] = "2.0"
        return data

    def get_refund_data(self, refund: OrderRefund):
        data = super()._get_refund_data(refund)
        data["RefNr"] = refund.full_id  # not for EVO
        data["OrderDesc"] = "Order {}-{}".format(self.event.slug.upper(), refund.full_id)
        return data


class ComputopGiropay(ComputopMethod):
    apiurl = "https://www.computop-paygate.com/giropay.aspx"
    extra_form_fields = []
