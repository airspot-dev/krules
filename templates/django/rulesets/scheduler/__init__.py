from django.apps import apps
from django.conf import settings

apps.populate(settings.INSTALLED_APPS)
