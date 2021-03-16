import os

import shutil
import logging

DJANGO_VERSION = "3.1.7"

def init_dir(p_root):

    logger = logging.getLogger(__name__)

    if "django_support" in [os.path.split(p)[-1] for p in p_root.iterdir()]:
        logger.warning("django_support already exists.. skipped")
        return
    m_dir = os.path.dirname(os.path.abspath(__file__))
    shutil.copytree(os.path.join(m_dir, "django_support"), p_root.joinpath("django_support"))
    logger.debug("added django_support folder")


ruleset__init_code = [
    'from django.apps import apps',
    'from django.conf import settings',
    'apps.populate(settings.INSTALLED_APPS)',
]

deploy__extra_commands = [
    ("RUN", f"pip install --no-cache-dir Django=={DJANGO_VERSION}")
]

deploy__labels = [
    ("config.krules.airspot.dev/django-orm", "inject"),
]

ishell__exec_lines = ruleset__init_code + [
    'from django_support.models import *'
]
