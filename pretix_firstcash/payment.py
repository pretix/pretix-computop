import hashlib
from base64 import b16encode
from collections import OrderedDict
from urllib.parse import urlencode

from Cryptodome.Hash import SHA256, HMAC
from Cryptodome.Util import Padding
from django import forms
from django.conf import settings
from django.http import HttpRequest
from django.template.loader import get_template

from django.utils.translation import gettext_lazy as _
from django_countries import countries

from Cryptodome.Cipher import Blowfish

from pretix.base.decimal import round_decimal
from pretix.base.forms import SecretKeySettingsField
from pretix.base.models import Event, OrderPayment, Order
from pretix.base.payment import BasePaymentProvider
from pretix.base.settings import SettingsSandbox
from pretix.multidomain.urlreverse import build_absolute_uri


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

    def _amount_to_decimal(self, cents):
        places = settings.CURRENCY_PLACES.get(self.event.currency, 2)
        return round_decimal(float(cents) / (10 ** places), self.event.currency)

    def _decimal_to_int(self, amount):
        places = settings.CURRENCY_PLACES.get(self.event.currency, 2)
        return int(amount * 10 ** places)

    def payment_form_render(self, request) -> str:
        template = get_template('pretix_firstcash/checkout_payment_form.html')
        return template.render()

    def checkout_prepare(self, request, cart):
        return True

    def payment_is_valid_session(self, request):
        return True

    def checkout_confirm_render(self, request, order: Order = None) -> str:
        template = get_template('pretix_firstcash/checkout_payment_confirm.html')
        ctx = {'request': request}
        return template.render(ctx)

    def execute_payment(self, request: HttpRequest, payment: OrderPayment) -> str:
        trans_id = payment.full_id
        ref_nr = payment.full_id
        return_url = build_absolute_uri(self.event, 'plugins:pretix_firstcash:return', kwargs={
            'order': payment.order.code,
            'hash': hashlib.sha1(payment.order.secret.lower().encode()).hexdigest(),
            'payment': payment.pk,
        })
        notify_url = build_absolute_uri(self.event, 'plugins:pretix_firstcash:notify', kwargs={
            'order': payment.order.code,
            'hash': hashlib.sha1(payment.order.secret.lower().encode()).hexdigest(),
            'payment': payment.pk,
        })
        data = urlencode({
            'MerchantID': self.settings.get('merchant_id'),
            'TransID': trans_id,
            'OrderDesc': ref_nr,  # put in simulation mode by setting 'Test:0000' -> successful, 'Test:0305' -> failure
            'RefNr': ref_nr,
            'Amount': self._decimal_to_int(payment.amount),
            'Currency': self.event.currency,
            'URLSuccess': return_url,
            'URLFailure': return_url,
            'URLNotify': notify_url,
            'MAC': self._calculate_mac(
                transaction_id=trans_id,
                payment_amount=str(self._decimal_to_int(payment.amount)),
                currency=self.event.currency),
            # todo 'Response': 'encrypted',
        })
        encrypted_data = self._encrypt(data)
        payload = urlencode({
            'MerchantID': self.settings.get('merchant_id'),
            'Len': encrypted_data[1],
            'Data': encrypted_data[0],
            # todo 'Language':
            # todo 'URLBack': redirect zurück zum shop, bei abbruchs
            # todo 'paymentTypes'
        })
        # todo: payment.info füllen
        return self.firstcash_url + '?' + payload


class FirstcashPayment(FirstcashMethod):
    identifier = '1cs'
    verbose_name = _('Payment via 1cs')
    public_name = _('Pay via 1cs')
    method = 'firstcash'
    firstcash_url = 'https://www.computop-paygate.com/paymentpage.aspx'


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
