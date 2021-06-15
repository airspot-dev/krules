from django.apps import apps
from django.conf import settings


def init():
    apps.populate(settings.INSTALLED_APPS)
