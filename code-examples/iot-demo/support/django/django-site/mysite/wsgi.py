import os

from django.core.wsgi import get_wsgi_application
from whitenoise import WhiteNoise

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mysite.settings")

application = get_wsgi_application()

base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
application = WhiteNoise(application, root=os.path.join(base, "static"))
