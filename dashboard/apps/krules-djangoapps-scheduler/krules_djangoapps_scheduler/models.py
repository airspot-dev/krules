from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from krules_djangoapps_common.fields import EmptyObjectJSONField
from krules_djangoapps_common.k8s import get_api, ContainerSource
import pykube
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

    period = models.IntegerField(default=5)

    def __str__(self):
        return "period: %d" % self.period


@receiver(post_save, sender=SchedulerConfig)
def update_heartbeat(sender, instance, created, **kwargs):

    api = get_api()
    try:
        obj = ContainerSource.objects(api).get_by_name("heartbeats")
        obj.obj["spec"]["template"]["spec"]["containers"][0]["args"][0] = "--period=%d" % instance.period
        obj.update()
    except pykube.exceptions.ObjectDoesNotExist:
        pass
