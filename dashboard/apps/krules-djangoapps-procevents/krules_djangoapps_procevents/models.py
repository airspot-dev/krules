from django.db import models
from krules_djangoapps_common.fields import EmptyObjectJSONField


class ProcessingEvent(models.Model):

    rule_name = models.CharField(max_length=255)
    type = models.CharField(max_length=255)
    subject = models.CharField(max_length=255)
    event_info = EmptyObjectJSONField(default=dict)
    payload = EmptyObjectJSONField(default=dict)
    time = models.DateTimeField()
    filters = EmptyObjectJSONField(default=list)
    processing = EmptyObjectJSONField(default=list)
    got_errors = models.BooleanField()
    passed = models.BooleanField()
    source = models.CharField(max_length=255, null=True, blank=True)
    origin_id = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return "{}:{}:{}:{}".format(
            self.passed and "process" or "pass",
            self.source,
            self.rule_name,
            str(self.subject),
        )