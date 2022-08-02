from django import forms
from django.utils.translation import gettext_lazy as _

from .payment import ComputopMethod, ComputopSettingsHolder, ComputopEDD, ComputopCC, ComputopGiropay

payment_methods = [
    {
        "method": "CC",
        "type": "meta",
        "public_name": _("Credit card"),
        "verbose_name": _("Credit card"),
        "baseclass": ComputopCC
    },
    # {
    #     "method": "ApplePay",
    #     "type": "scheme",
    #     "public_name": _("Apple Pay"),
    #     "verbose_name": _("Apple Pay"),
    # },
    # {
    #     "method": "GooglePay",
    #     "type": "scheme",
    #     "public_name": _("Google Pay"),
    #     "verbose_name": _("Google Pay"),
    # },
    {
        "method": "EDD",
        "type": "other",
        "public_name": _("SEPA Direct Debit"),
        "verbose_name": _("SEPA Direct Debit"),
        "baseclass": ComputopEDD
    },
    # {
    #     "method": "PayPal",
    #     "type": "other",
    #     "public_name": _("PayPal"),
    #     "verbose_name": _("PayPal"),
    # },
    # {
    #     "method": "iDEAL",
    #     "type": "other",
    #     "public_name": _("iDEAL"),
    #     "verbose_name": _("iDEAL"),
    # },
    # {
    #     "method": "Sofort",
    #     "type": "other",
    #     "public_name": _("SOFORT"),
    #     "verbose_name": _("SOFORT"),
    # },
    {
        "method": "giropay",
        "type": "other",
        "public_name": _("giropay"),
        "verbose_name": _("giropay"),
        "baseclass": ComputopGiropay
    },
    # {
    #     "method": "paydirekt",
    #     "type": "other",
    #     "public_name": _("paydirekt"),
    #     "verbose_name": _("paydirekt"),
    # },
    # {
    #     "method": "Alipay",
    #     "type": "other",
    #     "public_name": _("Alipay"),
    #     "verbose_name": _("Alipay"),
    # },
    # {
    #     "method": "BanconPP",
    #     "type": "other",
    #     "public_name": _("Bancontact"),
    #     "verbose_name": _("Bancontact"),
    # },
    # {
    #     "method": "BankTranPP",
    #     "type": "other",
    #     "public_name": _("SEPA Bank Transfer"),
    #     "verbose_name": _("SEPA Bank Transfer"),
    # },
    # {
    #     "method": "BitPayPP",
    #     "type": "other",
    #     "public_name": _("BitPay"),
    #     "verbose_name": _("BitPay"),
    # },
    # {
    #     "method": "DragonPP",
    #     "type": "other",
    #     "public_name": _("Dragonpay"),
    #     "verbose_name": _("Dragonpay"),
    # },
    # {
    #     "method": "ENETSPP",
    #     "type": "other",
    #     "public_name": _("eNETS"),
    #     "verbose_name": _("eNETS"),
    # },
    # {
    #     "method": "FinOBTPP",
    #     "type": "other",
    #     "public_name": _("Online Bank Transfer"),
    #     "verbose_name": _("Finland Online Bank Transfer"),
    # },
    # {
    #     "method": "IndoATMPP",
    #     "type": "other",
    #     "public_name": _("ATM"),
    #     "verbose_name": _("Indonesia ATM"),
    # },
    # {
    #     "method": "MultibanPP",
    #     "type": "other",
    #     "public_name": _("Multibanco"),
    #     "verbose_name": _("Multibanco"),
    # },
    # {
    #     "method": "MyBankPP",
    #     "type": "other",
    #     "public_name": _("My Bank"),
    #     "verbose_name": _("My Bank"),
    # },
    # {
    #     "method": "MyClearPP",
    #     "type": "other",
    #     "public_name": _("MyClear FPX"),
    #     "verbose_name": _("MyClear FPX"),
    # },
    # {
    #     "method": "P24PP",
    #     "type": "other",
    #     "public_name": _("Przelewy 24"),
    #     "verbose_name": _("Przelewy 24"),
    # },
    # {
    #     "method": "POLiPP",
    #     "type": "other",
    #     "public_name": _("POLi"),
    #     "verbose_name": _("POLi"),
    # },
    # {
    #     "method": "POSTFINPP",
    #     "type": "other",
    #     "public_name": _("PostFinance"),
    #     "verbose_name": _("PostFinance"),
    # },
    # {
    #     "method": "PSCPP",
    #     "type": "other",
    #     "public_name": _("paysafecard"),
    #     "verbose_name": _("paysafecard"),
    # },
    # {
    #     "method": "RHBBankPP",
    #     "type": "other",
    #     "public_name": _("RHB Bank"),
    #     "verbose_name": _("RHB Bank"),
    # },
    # {
    #     "method": "SafetyPPP",
    #     "type": "other",
    #     "public_name": _("SafetyPay"),
    #     "verbose_name": _("SafetyPay"),
    # },
    # {
    #     "method": "SevenElePP",
    #     "type": "other",
    #     "public_name": _("7-Eleven"),
    #     "verbose_name": _("7-Eleven"),
    # },
    # {
    #     "method": "SkrillPP",
    #     "type": "other",
    #     "public_name": _("Skrill"),
    #     "verbose_name": _("Skrill"),
    # },
    # {
    #     "method": "TrustPayPP",
    #     "type": "other",
    #     "public_name": _("TrustPay"),
    #     "verbose_name": _("TrustPay"),
    # },
    # {
    #     "method": "B4Payment",
    #     "type": "other",
    #     "public_name": _("B4Payment"),
    #     "verbose_name": _("B4Payment"),
    # },
    # {
    #     "method": "BoletoPP",
    #     "type": "other",
    #     "public_name": _("Boleto"),
    #     "verbose_name": _("Boleto"),
    # },
    # {
    #     "method": "CUPPP",
    #     "type": "other",
    #     "public_name": _("CUP"),
    #     "verbose_name": _("CUP"),
    # },
    # {
    #     "method": "EPS",
    #     "type": "other",
    #     "public_name": _("EPS"),
    #     "verbose_name": _("EPS"),
    #     "baseclass": ComputopEPS
    # },
    # {
    #     "method": "WechatPP",
    #     "type": "other",
    #     "public_name": _("Wechat"),
    #     "verbose_name": _("Wechat"),
    # },
]


def get_payment_method_classes(brand, payment_methods, baseclass, settingsholder):
    settingsholder.payment_methods_settingsholder = []
    for m in payment_methods:
        settingsholder.payment_methods_settingsholder.append(
            (
                "method_{}".format(m["method"]),
                forms.BooleanField(
                    label="{} {}".format(
                        '<span class="fa fa-credit-card"></span>'
                        if m["type"] in ["scheme", "meta"]
                        else "",
                        m["verbose_name"],
                    ),
                    help_text=_("Needs to be enabled in your payment provider's account first."),
                    required=False,
                ),
            )
        )
        if "baseclass" in m:
            for field in m["baseclass"].extra_form_fields:
                settingsholder.payment_methods_settingsholder.append(
                    (
                        "method_{}_{}".format(m["method"], field[0]),
                        field[1]
                    )
                )

    # We do not want the "scheme"-methods listed as a payment-method, since they are covered by the meta methods
    return [settingsholder] + [
        type(
            f'Computop{"".join(m["public_name"].split())}',
            (m["baseclass"] if "baseclass" in m else baseclass,),
            {
                "identifier": "{payment_provider}_{payment_method}".format(
                    payment_method=m["method"], payment_provider=brand.lower()
                ),
                "verbose_name": _("{payment_method} via {payment_provider}").format(
                    payment_method=m["verbose_name"], payment_provider=brand
                ),
                "public_name": m["public_name"],
                "method": m["method"],
                "type": m["type"],
            },
        )
        for m in payment_methods
        if m["type"] != "scheme"
    ]


payment_method_classes = get_payment_method_classes(
    "Computop", payment_methods, ComputopMethod, ComputopSettingsHolder
)
