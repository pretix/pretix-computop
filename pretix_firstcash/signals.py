from django.dispatch import receiver

from pretix.base.signals import register_payment_providers


@receiver(register_payment_providers, dispatch_uid="payment_firstcash")
def register_payment_provider(sender, **kwargs):
    from .payment import (
        FirstcashSettingsHolder, FirstcashPayment, FirstcashCC, FirstcashGiropay, FirstcashDirectDebit
    )
    return [
        FirstcashSettingsHolder, FirstcashPayment, FirstcashCC, FirstcashGiropay, FirstcashDirectDebit
    ]
