
# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
from krules_core.providers import configs_factory

#BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from django.core.management.utils import get_random_secret_key
SECRET_KEY = get_random_secret_key()

ALLOWED_HOSTS = []

# Application definition
INSTALLED_APPS = [
    "django_support",
]

DATABASES = configs_factory().get("django", {}).get("databases", {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'db.sqlite3',
    }
})

USE_TZ = True
TIME_ZONE = "UTC"
