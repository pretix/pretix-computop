from pretix_computop.paymentmethods import (
    get_payment_method_classes,
    payment_methods as payment_methods_repo,
)

from .payment import ComputopMethod, FirstcashSettingsHolder

supported_methods = [
    # Meta-Scheme
    "CC",
    # Scheme
    # 'ApplePay',  # Coming soon
    # 'GooglePay',  # Coming soon
    # The rest
    "EDD",
    "PayPal",
    "iDEAL",
    "Sofort",
    "giropay",
    "paydirekt",
    # 'Alipay',  # Coming soon
    "POSTFINPP",
    # 'CUPPP',  # Coming soon
    "EPS",
    # 'WechatPP',  # Coming soon
    # amazonpay coming soon, too - but not a HPP-method?
]
payment_methods = [
    item for item in payment_methods_repo if item.get("method") in supported_methods
]

payment_method_classes = get_payment_method_classes(
    "Firstcash", payment_methods, ComputopMethod, FirstcashSettingsHolder
)
