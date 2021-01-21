from django.db import models
from django.contrib.postgres.fields import JSONField


class Service(models.Model):
	name = models.CharField(max_length=50, unique=True)
	image = models.CharField(max_length=255, default="gcr.io/knative-samples/knative-route-demo:blue")
	t_version = models.CharField(max_length=255, verbose_name="T_VERSION", default="blue")


class Configuration(models.Model):
	service = models.ForeignKey(Service, on_delete=models.CASCADE)
	name = models.CharField(max_length=255, unique=True)
	image = models.CharField(max_length=255, unique=True)
	env = JSONField()
	traffic = models.IntegerField(default=100)
