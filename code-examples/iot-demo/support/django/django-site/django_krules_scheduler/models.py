from django.db import models
from django.contrib.postgres.fields import JSONField
from uuid import uuid4


class ScheduledEvent(models.Model):

    uid = models.CharField(max_length=255, primary_key=True, default=uuid4)
    event_type = models.CharField(max_length=255)
    subject = models.CharField(max_length=255)
    payload = JSONField()
    origin_id = models.CharField(max_length=255)
    when = models.DateTimeField()
