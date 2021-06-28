# Generated by Django 3.2.4 on 2021-06-14 12:20

from django.db import migrations, models
import krules_djangoapps_common.fields


class Migration(migrations.Migration):

    dependencies = [
        ('krules_djangoapps_scheduler', '0002_schedulerconfig_data_migration'),
    ]

    operations = [
        migrations.AddField(
            model_name='scheduledevent',
            name='subject_key',
            field=models.CharField(blank=True, help_text='Uniquely identifies one task per subject', max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='scheduledevent',
            name='payload',
            field=krules_djangoapps_common.fields.EmptyObjectJSONField(default=dict),
        ),
        migrations.AlterUniqueTogether(
            name='scheduledevent',
            unique_together={('subject', 'subject_key')},
        ),
    ]
