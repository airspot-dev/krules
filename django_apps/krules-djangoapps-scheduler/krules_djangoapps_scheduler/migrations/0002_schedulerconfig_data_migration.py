from __future__ import unicode_literals

from django.db import migrations


def create_default_config(apps, schema_editor):
    SchedulerConfig = apps.get_model("krules_djangoapps_scheduler", "SchedulerConfig")
    if SchedulerConfig.objects.count() == 0:
        SchedulerConfig.objects.get_or_create(period=5)


class Migration(migrations.Migration):

    dependencies = [
        ('krules_djangoapps_scheduler', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_default_config),
    ]
