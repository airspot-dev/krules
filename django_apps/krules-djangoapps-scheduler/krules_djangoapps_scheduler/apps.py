from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class SchedulerAppConfig(AppConfig):
    name = 'krules_djangoapps_scheduler'
    verbose_name = _('KRules scheduled events')
