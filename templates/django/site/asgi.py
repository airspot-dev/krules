import os
from django.core.asgi import get_asgi_application

app = get_asgi_application()

from channels.routing import ProtocolTypeRouter

application = ProtocolTypeRouter({
    "http": app
})