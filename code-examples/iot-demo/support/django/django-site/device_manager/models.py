from django.db import models


class Fleet(models.Model):

    name = models.CharField(max_length=255, primary_key=True)
    api_key = models.CharField(max_length=255)
    endpoint = models.URLField(max_length=255, default="")
    dashboard = models.URLField(max_length=255, default="")
    cluster_local = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "fleet middleware"
        verbose_name_plural = "fleet middleware"


class ReceivedData(models.Model):

    owner = models.CharField(max_length=255)
    device = models.CharField(max_length=255)
    data = models.JSONField()
    timestamp = models.DateTimeField()

    class Meta:
        verbose_name_plural = "received data"


class LocationTrackerService(models.Model):

    name = models.CharField(max_length=255)
    maintenance = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = "location tracker service"


class LocationTrackerData(models.Model):

    owner = models.CharField(max_length=255)
    device = models.CharField(max_length=255)
    coords = models.CharField(max_length=255)
    location = models.CharField(max_length=255)
    timestamp = models.DateTimeField()

    class Meta:
        verbose_name_plural = "location tracker data"
