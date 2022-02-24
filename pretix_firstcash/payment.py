from base64 import b16encode
from collections import OrderedDict

from Cryptodome.Hash import SHA256, HMAC
from Cryptodome.Util import Padding
from django import forms
from django.http import HttpRequest
from django.template.loader import get_template

from django.utils.translation import gettext_lazy as _
from django_countries import countries

from Cryptodome.Cipher import Blowfish

from pretix.base.forms import SecretKeySettingsField
from pretix.base.models import Event, OrderPayment
from pretix.base.payment import BasePaymentProvider
from pretix.base.settings import SettingsSandbox


class FirstcashSettingsHolder(BasePaymentProvider):
    identifier = 'firstcash_settings'
    verbose_name = _('Firstcash')
    is_enabled = False
    is_meta = True

    def __init__(self, event: Event):
        super().__init__(event)
        self.settings = SettingsSandbox('payment', 'firstcash', event)

    @property
    def settings_form_fields(self):
        allcountries = list(countries)
        allcountries.insert(0, ('', _('Select country')))

        fields = [
            ('merchant_id',
             forms.CharField(
                 label=_('Merchant ID'),
                 validators=(),
             )),
            ('blowfish_password',
             SecretKeySettingsField(
                 label=_('Blowfish Password'),
                 validators=(),
             )),
            ('hmac_password',
             SecretKeySettingsField(
                 label=_('Secret key'),
                 validators=(),
             )),
        ]
        d = OrderedDict(
            fields + [
                ('method_firstcash',
                 forms.BooleanField(
                     label=_('Payments via 1cs'),
                     required=False,
                 )),
                ('method_firstcash_cc',
                 forms.BooleanField(
                     label=_('Credit card payments via 1cs'),
                     required=False,
                 )),
                ('method_firstcash_giropay',
                 forms.BooleanField(
                     label=_('Giropay payments via 1cs'),
                     required=False,
                 )),
                ('method_firstcash_dd',
                 forms.BooleanField(
                     label=_('Direct debit payments via 1cs'),
                     required=False,
                 )),
            ] + list(super().settings_form_fields.items())
        )

        d.move_to_end('_enabled', last=False)
        return d


class FirstcashMethod(BasePaymentProvider):
    identifier = ''
    method = ''

    def __init__(self, event: Event):
        super().__init__(event)
        self.settings = SettingsSandbox('payment', 'firstcash', event)

    @property
    def settings_form_fields(self):
        return {}

    @property
    def is_enabled(self) -> bool:
        return self.settings.get('_enabled', as_type=bool) and self.settings.get('method_{}'.format(self.method),
                                                                                 as_type=bool)

    def _payment_parameters(self, request: HttpRequest, payment: OrderPayment):
        # Mandatory and encrypted
        mand = [
            ('merchant_id', self.settings.get('merchant_id')),
            ('amount', payment.amount),
            ('currency', ''),
            ('mac', self._calculate_mac(payment)),
            ('transaction_id', ''),
            ('order_description', 'OrderDesc=Test:0000'),
            # puts payment in simulation mode (0000 -> successful, 0305 -> failure)
            # ('url_success', build_absolute_uri(
            #     request.event,
            #     "plugins:pretix_computop:return",
            #     kwargs={
            #         "order": payment.order.code,
            #         "payment": payment.pk,
            #         "hash": hashlib.sha1(
            #             payment.order.secret.lower().encode()
            #         ).hexdigest(),
            #     },
            # )),
            # ('url_failure', build_absolute_uri(
            #     request.event,
            #     "plugins:pretix_computop:return",
            #     kwargs={
            #         "order": payment.order.code,
            #         "payment": payment.pk,
            #         "hash": hashlib.sha1(
            #             payment.order.secret.lower().encode()
            #         ).hexdigest(),
            #     },
            # )),
            # ('url_notify', build_absolute_uri(
            #     request.event,
            #     "plugins:pretix_computop:notify",
            #     kwargs={
            #         "order": payment.order.code,
            #         "payment": payment.pk,
            #         "hash": hashlib.sha1(
            #             payment.order.secret.lower().encode()
            #         ).hexdigest(),
            #     },
            # )),
        ]
        mand_str = ''
        for key, value in mand:
            mand_str = mand_str + '&' + key + '=' + str(value)

        # Optional but encrypted
        opt_enc = [
            ('reference_number', None),
            ('user_data', None),
            ('response', 'Response=encrypt'),
        ]
        opt_enc_str = ''
        for key, value in opt_enc:
            if value is not None:
                opt_enc_str = opt_enc_str + '&' + key + '=' + str(value)

        # Optional and not encrypted
        opt = [
            ('language', None),
            ('url_back', None),  # URL to redirect to if customer cancels before paying
            ('payment_types', None),  # override configured payment types with this parameter
        ]
        opt_str = ''
        for key, value in opt:
            if value is not None:
                opt_str = opt_str + '&' + key + '=' + str(value)

        enc_str = self._encrypt(mand_str + opt_enc_str)

        return enc_str + opt_str

    def _encrypt(self, plaintext):
        key = self.settings.get('blowfish_password').encode('UTF-8')
        cipher = Blowfish.new(key, Blowfish.MODE_ECB)
        bs = Blowfish.block_size
        padded_text = Padding.pad(plaintext.encode('UTF-8'), bs)
        encrypted_text = cipher.encrypt(padded_text)
        return b16encode(encrypted_text).decode(), len(plaintext)

    def _calculate_mac(self, payment_id='', transaction_id='', payment_amount='', currency=''):
        pay_id = str(payment_id)
        trans_id = str(transaction_id)
        merchant_id = self.settings.get('merchant_id')
        amount = str(payment_amount)
        plain = (pay_id + '*' + trans_id + '*' + merchant_id + '*' + amount + '*' + currency).encode('UTF-8')
        secret = self.settings.get('hmac_password').encode('UTF-8')
        h = HMAC.new(secret, digestmod=SHA256)
        h.update(plain)
        return h.hexdigest()

    def payment_form_render(self, request) -> str:
        template = get_template('pretix_firstcash/checkout_payment_form.html')
        return template.render()

    # def checkout_prepare(self, request: HttpRequest, cart: Dict[str, Any]) -> Union[bool, str]:
    #     print(self._encrypt('MerchantID=1CS_test_rami_GmbH&TransID=1234&RefNr=4321&Amount=123&Currency=EUR&URLBack'
    #                         '=https://www.paytest.org/ct-test/index.php&URLSuccess=https://www.paytest.org/ct-test'
    #                         '/success.php&URLFailure=https://www.paytest.org/ct-test/failure.php&URLNotify=https'
    #                         '://www.paytest.org/ct-test/notify.php&MAC='
    #                         + self._calculate_mac(transaction_id=str(1234), payment_amount=str(123), currency='EUR')))
    #     return

    # def api_payment_details(self, payment: OrderPayment):
    #     return {
    #         "id": payment.info_data.get("id", None),
    #         "payment_method": payment.info_data.get("payment_method", None)
    #     }
    #
    # def matching_id(self, payment: OrderPayment):
    #     return payment.info_data.get("id", None)


class FirstcashPayment(FirstcashMethod):
    identifier = '1cs'
    verbose_name = _('Payment via 1cs')
    public_name = _('Pay via 1cs')
    method = 'firstcash'
    firstcash_url = 'https://www.computop-paygate.com/paymeentpage.aspx'


class FirstcashCC(FirstcashMethod):
    identifier = 'firstcash_cc'
    verbose_name = _('Credit card payment via 1cs')
    public_name = _('Credit card')
    method = 'firstcash_cc'
    firstcash_url = 'https://www.computop-paygate.com/payssl.aspx'


class FirstcashGiropay(FirstcashMethod):
    identifier = 'firstcash_giropay'
    verbose_name = _('Giropay payment via 1cs')
    public_name = _('giropay')
    method = 'firstcash_giropay'
    firstcash_url = 'https://www.computop-paygate.com/giropay.aspx'


class FirstcashDirectDebit(FirstcashMethod):
    identifier = 'firstcash_dd'
    verbose_name = _('Direct debit payment via 1cs')
    public_name = _('Direct Debit')
    method = 'firstcash_dd'
    firstcash_url = 'https://www.computop-paygate.com/paysdd.aspx'
