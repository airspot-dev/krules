
import os
from krules_core.providers import configs_factory

configuration_key = os.environ.get("CONFIGURATION_KEY")

site_config = configs_factory().get(configuration_key, {}).get("site_settings", {})

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


from django.core.management.utils import get_random_secret_key
SECRET_KEY = site_config.get('secret_key', get_random_secret_key())

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = bool(eval(os.environ.get("DEBUG", site_config.get('debug', "False"))))

INSTALLED_APPS = [
    'krules_djangoapps_common',
    'krules_djangoapps_scheduler',
]

# Database
# https://docs.djangoproject.com/en/2.1/ref/settings/#databases
DATABASES = site_config.get("databases", {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'db.sqlite3',
    }
})

LANGUAGE_CODE = os.environ.get("LANGUAGE_CODE", site_config.get("language_code", 'en-us'))
TIME_ZONE = os.environ.get("TIME_ZONE", site_config.get("time_zone", 'UTC'))
USE_I18N = True
USE_L10N = True
USE_TZ = True