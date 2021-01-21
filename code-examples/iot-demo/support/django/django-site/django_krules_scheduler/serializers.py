from rest_framework import serializers
from .models import ScheduledEvent


class ScheduledEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScheduledEvent
        fields = [
            'uid', 'event_type', 'subject', 'payload', 'origin_id', 'when'
        ]
