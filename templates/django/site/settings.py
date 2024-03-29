
import os
import logging.config
import krules_env
from krules_core.providers import configs_factory

krules_env.init()

configuration_key = os.environ.get("CONFIGURATION_KEY", "django")
site_name = os.environ.get("SITE_NAME", "djsite")

site_config = configs_factory().get(configuration_key, {}).get("site_settings", {})

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


from django.core.management.utils import get_random_secret_key
SECRET_KEY = site_config.get('secret_key', get_random_secret_key())

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = bool(eval(os.environ.get("DEBUG", site_config.get('debug', "False"))))

ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", site_config.get('allowed_hosts', ['*']))
if isinstance(ALLOWED_HOSTS, type("")):
    ALLOWED_HOSTS = ALLOWED_HOSTS.split()


# Application definition
INSTALLED_APPS = site_config.get(
    "installed_apps",
    [
        #'channels',
        'django.contrib.admin',
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
        'django.contrib.messages',
        'django.contrib.staticfiles',
        #'django_json_widget',
        #'prettyjson',
        #'rest_framework',
        #'djangochannelsrestframework',
        #'jsoneditor',
    ]
)

MIDDLEWARE = site_config.get(
    "middleware",
    [
        'django.middleware.security.SecurityMiddleware',
        'whitenoise.middleware.WhiteNoiseMiddleware',
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.middleware.common.CommonMiddleware',
        'django.middleware.csrf.CsrfViewMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        'django.contrib.messages.middleware.MessageMiddleware',
        'django.middleware.clickjacking.XFrameOptionsMiddleware',
    ]
)

ROOT_URLCONF = os.environ.get("ROOT_URLCONF", site_config.get("root_urlconf", f'{site_name}.urls'))

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = '{{ site_name }}.wsgi.application'
ASGI_APPLICATION = '{{ site_name }}.asgi.application'

# Database
# https://docs.djangoproject.com/en/2.1/ref/settings/#databases
DATABASES = site_config.get("databases", {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'db.sqlite3',
    }
})

# Password validation
# https://docs.djangoproject.com/en/2.1/ref/settings/#auth-password-validators
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/2.1/topics/i18n/
LANGUAGE_CODE = os.environ.get("LANGUAGE_CODE", site_config.get("language_code", 'en-us'))

TIME_ZONE = os.environ.get("TIME_ZONE", site_config.get("time_zone", 'UTC'))

USE_I18N = True

USE_L10N = True

USE_TZ = True


STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

STATIC_URL = os.path.join(BASE_DIR, 'static/')
STATIC_ROOT = os.path.join(BASE_DIR, 'static/')

# Logging Configuration

# Clear prev config
LOGGING_CONFIG = None

# Get loglevel from env
LOGLEVEL = os.environ.get("DJANGO_LOGLEVEL", site_config.get('loglevel', 'info')).upper()

logging.config.dictConfig(site_config.get('logging_config', {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'console': {
            'format': '%(asctime)s %(levelname)s [%(name)s:%(lineno)s] %(module)s %(process)d %(thread)d %(message)s',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'console',
        },
    },
    'loggers': {
        '': {
            'level': LOGLEVEL,
            'handlers': ['console', ],
        },
    },
}))

