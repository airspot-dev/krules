import sys
from pathlib import Path
from krules_dev import sane_utils

sane_utils.load_env()

apps_dir = Path(__file__).resolve().parent
sys.path.append(str(apps_dir))


INSTALLED_APPS = [

]



DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': apps_dir.joinpath('db.sqlite3'),
    }
}


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
