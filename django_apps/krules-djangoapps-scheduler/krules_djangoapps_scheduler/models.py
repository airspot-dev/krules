from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

from krules_core.providers import subject_factory
from krules_djangoapps_common.fields import EmptyObjectJSONField
#from krules_djangoapps_common.k8s import get_api, ContainerSource
from uuid import uuid4


class ScheduledEvent(models.Model):

    uid = models.CharField(max_length=255, primary_key=True, default=uuid4)
    event_type = models.CharField(max_length=255)
    subject = models.CharField(max_length=255)
    subject_key = models.CharField(max_length=255, blank=True, null=True,
                                   help_text="Uniquely identifies one task per subject")
    payload = EmptyObjectJSONField(default=dict)
    origin_id = models.CharField(max_length=255)
    when = models.DateTimeField()

    class Meta:
        unique_together = ["subject", "subject_key"]


class SchedulerConfig(models.Model):

    period = models.IntegerField(default=2)

    def __str__(self):
        return "period: %d" % self.period

    def save(self, *args, **kwargs):
        subject = subject_factory("djangomodel:schedulerconfig")
        subject.set_ext("djangomodel", "schedulerconfig")
        subject.set("period", self.period)
        super().save(*args, **kwargs)

