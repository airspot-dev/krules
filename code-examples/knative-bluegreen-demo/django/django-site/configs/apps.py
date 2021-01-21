# Copyright 2015 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from django.apps import AppConfig


class ConfigsAppConfig(AppConfig):
    name = 'configs'

    def ready(self):
        from .models import Service, Configuration
        from django_signals_cloudevents import send_cloudevent
        from django.db.models.signals import post_save, post_delete
        post_save.connect(send_cloudevent, sender=Service)
        post_delete.connect(send_cloudevent, sender=Service)
        post_save.connect(send_cloudevent, sender=Configuration)
        post_delete.connect(send_cloudevent, sender=Configuration)
