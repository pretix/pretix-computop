import hashlib
import importlib
import json
from base64 import b16encode, b16decode
from collections import OrderedDict
from decimal import Decimal
from urllib.parse import urlencode

from Crypto.Hash import SHA256, HMAC
from Crypto.Util import Padding
from django import forms
from django.conf import settings
from django.http import HttpRequest
from django.template.loader import get_template

from django.utils.translation import gettext_lazy as _

from Crypto.Cipher import Blowfish

from pretix.base.decimal import round_decimal
from pretix.base.forms import SecretKeySettingsField
from pretix.base.models import Event, OrderPayment, Order
from pretix.base.payment import BasePaymentProvider
from pretix.base.settings import SettingsSandbox
from pretix.multidomain.urlreverse import build_absolute_uri


class ComputopSettingsHolder(BasePaymentProvider):
    identifier = 'computop_settings'
    verbose_name = _('Computop')
    is_enabled = False
    is_meta = True
    payment_methods_settingsholder = []

    def __init__(self, event: Event):
        super().__init__(event)
        self.settings = SettingsSandbox('payment', self.identifier.split('_')[0], event)

    @property
    def settings_form_fields(self):
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
            fields + self.payment_methods_settingsholder + list(super().settings_form_fields.items())
        )
        d.move_to_end('_enabled', last=False)
        return d


class ComputopMethod(BasePaymentProvider):
    identifier = ''
    method = ''
    verbose_name = ''
    apiurl = 'https://www.computop-paygate.com/paymentpage.aspx'

    def __init__(self, event: Event):
        super().__init__(event)
        self.settings = SettingsSandbox('payment', self.identifier.split('_')[0], event)

    @property
    def settings_form_fields(self):
        return {}

    @property
    def is_enabled(self) -> bool:
        if self.type == 'meta':
            module = importlib.import_module(
                __name__.replace('computop', self.identifier.split('_')[0]).replace('.payment', '.paymentmethods')
            )
            for method in list(filter(lambda d: d['type'] in ['meta', 'scheme'], module.payment_methods)):
                if self.settings.get('_enabled', as_type=bool) and self.settings.get(
                        'method_{}'.format(method['method']), as_type=bool):
                    return True
            return False
        else:
            return self.settings.get('_enabled', as_type=bool) and self.settings.get(
                'method_{}'.format(self.method),
                as_type=bool)

    def _encrypt(self, plaintext):
        key = self.settings.get('blowfish_password').encode('UTF-8')
        cipher = Blowfish.new(key, Blowfish.MODE_ECB)
        bs = Blowfish.block_size
        padded_text = Padding.pad(plaintext.encode('UTF-8'), bs)
        encrypted_text = cipher.encrypt(padded_text)
        return b16encode(encrypted_text).decode(), len(plaintext)

    def decrypt(self, ciphertext):
        key = self.settings.get('blowfish_password').encode('UTF-8')
        cipher = Blowfish.new(key, Blowfish.MODE_ECB)
        bs = Blowfish.block_size
        ciphertext_bytes = b16decode(ciphertext)
        decrypted_text = cipher.decrypt(ciphertext_bytes)
        try:
            unpadded_text = Padding.unpad(decrypted_text, bs)
        except ValueError:
            unpadded_text = decrypted_text.rstrip()  # sometimes bs and padding are wrong, we strip ending spaces then
        return unpadded_text.decode('UTF-8')

    def _calculate_hmac(self, payment_id='', transaction_id='', amount_or_status='', currency_or_code=''):
        merchant_id = self.settings.get('merchant_id')
        cat = (str(payment_id) + '*' + str(transaction_id) + '*' + merchant_id + '*' + str(amount_or_status) + '*'
               + str(currency_or_code))
        plain = cat.encode('UTF-8')
        secret = self.settings.get('hmac_password').encode('UTF-8')
        h = HMAC.new(secret, digestmod=SHA256)
        h.update(plain)
        return h.hexdigest()

    def _amount_to_decimal(self, cents):
        places = settings.CURRENCY_PLACES.get(self.event.currency, 2)
        return round_decimal(float(cents) / (10 ** places), self.event.currency)

    def _decimal_to_int(self, amount):
        places = settings.CURRENCY_PLACES.get(self.event.currency, 2)
        return int(amount * 10 ** places)

    def payment_form_render(self, request: HttpRequest, total: Decimal, order: Order = None) -> str:
        template = get_template('pretix_computop/checkout_payment_form.html')
        return template.render()

    def checkout_prepare(self, request, cart):
        return True

    def payment_is_valid_session(self, request):
        return True

    def checkout_confirm_render(self, request, order: Order = None) -> str:
        template = get_template('pretix_computop/checkout_payment_confirm.html')
        ctx = {'request': request}
        return template.render(ctx)

    def execute_payment(self, request: HttpRequest, payment: OrderPayment) -> str:
        ident = self.identifier.split('_')[0]
        trans_id = payment.full_id
        ref_nr = payment.full_id
        return_url = build_absolute_uri(self.event, 'plugins:pretix_{}:return'.format(ident), kwargs={
            'order': payment.order.code,
            'hash': hashlib.sha1(payment.order.secret.lower().encode()).hexdigest(),
            'payment': payment.pk,
            'payment_provider': ident,
        })
        notify_url = build_absolute_uri(self.event, 'plugins:pretix_{}:notify'.format(ident), kwargs={
            'order': payment.order.code,
            'hash': hashlib.sha1(payment.order.secret.lower().encode()).hexdigest(),
            'payment': payment.pk,
            'payment_provider': ident,
        })
        data = {
            'MerchantID': self.settings.get('merchant_id'),
            'TransID': trans_id,
            'OrderDesc': 'Test:0000',
            # put in simulation mode by setting 'Test:0000' -> successful, 'Test:0305' -> failure
            'MsgVer': '2.0',
            'RefNr': ref_nr,
            'Amount': self._decimal_to_int(payment.amount),
            'Currency': self.event.currency,
            'URLSuccess': return_url,
            'URLFailure': return_url,
            'URLNotify': notify_url,
            'MAC': self._calculate_hmac(
                transaction_id=trans_id,
                amount_or_status=str(self._decimal_to_int(payment.amount)),
                currency_or_code=self.event.currency),
            'Response': 'encrypt',
        }
        encrypted_data = self._encrypt(urlencode(data))
        payload = {
            'MerchantID': self.settings.get('merchant_id'),
            'Len': encrypted_data[1],
            'Data': encrypted_data[0],
            'URLBack': return_url,  # wrong redirect when encrypted, check back later if fixed in computop
            'Language': payment.order.locale[:2],  # todo: Can this be moved to encrypted data?
            #'PayTypes': self.get_paytypes()  # todo: Can this be moved to encrypted data? # ToDo: The | should not be urlencoded # todo: breaks, need to wait for mail reply to fix
        }
        payment.info = json.dumps({
            'data': data,
            'encrypted_data': encrypted_data,
            'payload': payload,
        })
        payment.save(update_fields=['info'])
        return self.apiurl + '?' + urlencode(payload)

    def check_hash(self, payload_parsed):
        mid = payload_parsed['mid'][0]
        mac = str(payload_parsed['MAC'][0]).lower().rstrip()
        trans_id = payload_parsed['TransID'][0]
        pay_id = payload_parsed['PayID'][0]
        status = payload_parsed['Status'][0]
        code = payload_parsed['Code'][0]
        if mid == self.settings.get('merchant_id') and mac == self._calculate_hmac(pay_id, trans_id, status, code):
            return True
        else:
            return False

    def get_paytypes(self):
        if self.type == 'meta':
            paytypes = []
            module = importlib.import_module(
                __name__.replace('computop', self.identifier.split('_')[0]).replace('.payment', '.paymentmethods')
            )
            for method in list(filter(lambda d: d['type'] in ['meta', 'scheme'], module.payment_methods)):
                if self.settings.get('_enabled', as_type=bool) and self.settings.get('method_{}'.format(method['method']), as_type=bool):
                    paytypes.append(method['method'])

            return "|".join(paytypes)
        else:
            return self.method
