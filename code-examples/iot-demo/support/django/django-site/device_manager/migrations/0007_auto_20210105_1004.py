# Generated by Django 3.0.2 on 2021-01-05 10:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('device_manager', '0006_auto_20210105_0926'),
    ]

    operations = [
        migrations.AlterField(
            model_name='device',
            name='fleet',
            field=models.CharField(max_length=255),
        ),
        migrations.AlterField(
            model_name='receiveddata',
            name='device',
            field=models.CharField(max_length=255),
        ),
    ]
