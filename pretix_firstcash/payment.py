import logging
from django.utils.translation import gettext_lazy as _

from pretix_computop.payment import (
    ComputopMethod as SuperComputopMethod,
    ComputopSettingsHolder,
)

logger = logging.getLogger("pretix_firstcash")


class FirstcashSettingsHolder(ComputopSettingsHolder):
    identifier = "firstcash_settings"
    verbose_name = _("First Cash Solution")
    is_enabled = False
    is_meta = True


class ComputopMethod(SuperComputopMethod):
    identifier = "firstcash"
