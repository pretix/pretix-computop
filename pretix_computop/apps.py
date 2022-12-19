from django.utils.translation import gettext_lazy
from . import __version__

try:
    from pretix.base.plugins import PluginConfig
except ImportError:
    raise RuntimeError("Please use pretix 2.7 or above to run this plugin!")


class PluginApp(PluginConfig):
    default = True
    default = True
    name = "pretix_computop"
    verbose_name = "Computop payments for pretix"

    class PretixPluginMeta:
        name = gettext_lazy("Computop")
        author = "pretix team"
        description = gettext_lazy(
            "Use Computop-based payment providers"
        )
        visible = True
        version = __version__
        category = "PAYMENT"
        picture = "pretix_computop/logo.svg"
        compatibility = "pretix>=2.7.0"

    def ready(self):
        from . import signals  # NOQA

