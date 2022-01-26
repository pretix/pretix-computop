from collections import OrderedDict
from decimal import Decimal

from django import forms
from django.http import HttpRequest
from django.template.loader import get_template

from django.utils.translation import gettext_lazy as _
from django_countries import countries

from pretix.base.forms import SecretKeySettingsField
from pretix.base.models import Order, Event
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
            fields + list(super().settings_form_fields.items())
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

    def payment_form_render(self, request: HttpRequest, total: Decimal, order: Order = None) -> str:
        template = get_template('pretix_firstcash/checkout_payment_form.html')
        ctx = {'request': request, 'event': self.event, 'settings': self.settings}
        return template.render(ctx)


class FirstcashPayment(FirstcashMethod):
    identifier = '1cs'
    verbose_name = _('Payment via 1cs')
    public_name = _('1cs')
    method = ''
