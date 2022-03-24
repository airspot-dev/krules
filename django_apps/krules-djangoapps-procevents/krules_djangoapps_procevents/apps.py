from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ProcEventsAppConfig(AppConfig):
    name = 'krules_djangoapps_procevents'
    verbose_name = _('KRules processing events')