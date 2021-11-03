from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class CommonAppConfig(AppConfig):
    name = 'krules_djangoapps_common'
    verbose_name = _('KRules commons')