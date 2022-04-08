from pretix_computop.paymentmethods import (
    get_payment_method_classes, payment_methods as payment_methods_repo,
)

from .payment import ComputopMethod, FirstcashSettingsHolder

supported_methods = [
    # Meta-Scheme
    'CC',

    # Scheme
    'ApplePay',
    'GooglePay',

    # The rest
    'EDD',
    'PayPal',
    'iDEAL',
    'Sofort',
    'giropay',
    'paydirekt',
    'Alipay',
    'BanconPP',
    'BankTranPP',
    'BitPayPP',
    'DragonPP',
    'ENETSPP',
    'FinOBTPP',
    'IndoATMPP',
    'MultibanPP',
    'MyBankPP',
    'MyClearPP',
    'P24PP',
    'POLiPP',
    'POSTFINPP',
    'PSCPP',
    'RHBBankPP',
    'SafetyPPP',
    'SevenElePP',
    'SkrillPP',
    'TrustPayPP',
    'B4Payment',
    'BoletoPP',
    'CUPPP',
    'EPS',
    'WechatPP',
]
payment_methods = [item for item in payment_methods_repo if item.get('method') in supported_methods]

payment_method_classes = get_payment_method_classes('Firstcash', payment_methods, ComputopMethod, FirstcashSettingsHolder)
