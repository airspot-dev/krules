import os

from django.core.asgi import get_asgi_application
from whitenoise import WhiteNoise

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')

application = get_asgi_application()
base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
application = WhiteNoise(application, root=os.path.join(base, "static"))
