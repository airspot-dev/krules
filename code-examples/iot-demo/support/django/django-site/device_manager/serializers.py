from rest_framework import serializers
from .models import Fleet, ReceivedData


class FleetSerializer(serializers.ModelSerializer):

    class Meta:
        model = Fleet
        fields = [
            'name', 'api_key', 'endpoint', 'dashboard', 'cluster_local',
        ]


class ReceivedDataSerializer(serializers.ModelSerializer):

    class Meta:
        model = ReceivedData
        fields = [
            'device', 'owner', 'data', 'timestamp',
        ]
