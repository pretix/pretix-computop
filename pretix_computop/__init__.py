from django.utils.translation import gettext_lazy

try:
    from pretix.base.plugins import PluginConfig
except ImportError:
    raise RuntimeError("Please use pretix 2.7 or above to run this plugin!")

__version__ = "1.0.0"


class PluginApp(PluginConfig):
    name = "pretix_computop"
    verbose_name = "Computop payments for pretix"

    class PretixPluginMeta:
        name = gettext_lazy("Computop")
        author = "Phin Wolkwitz"
        description = gettext_lazy("This plugin allows you to use Computop-based payment providers")
        visible = True
        version = __version__
        category = "PAYMENT"
        picture = "pretix_computop/logo.svg"
        compatibility = "pretix>=2.7.0"

    def ready(self):
        from . import signals  # NOQA


default_app_config = "pretix_computop.PluginApp"
