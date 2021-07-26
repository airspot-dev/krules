"""mysite URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, re_path, reverse_lazy, include
from django.views.generic import RedirectView
import os

configuration_key = os.environ.get("CONFIGURATION_KEY", "django")

from krules_core.providers import configs_factory
url_settings = configs_factory().get(configuration_key, {}).get("url_settings", {})

urlpatterns = []

if url_settings.get("enable_admin", False):
    urlpatterns.append(path('admin/', admin.site.urls))
if url_settings.get("root_redirect"):
    urlpatterns.append(re_path(r'^$', RedirectView.as_view(url=reverse_lazy(url_settings.get("root_redirect")))))
for p in url_settings.get("path_includes", []):
    urlpatterns.append(
        path(p["path"], include(p["include"]))
    )


