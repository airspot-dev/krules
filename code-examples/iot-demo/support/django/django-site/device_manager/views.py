from rest_framework import viewsets
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import HTTP_503_SERVICE_UNAVAILABLE, HTTP_201_CREATED
from rest_framework.views import APIView

from .serializers import FleetSerializer, ReceivedDataSerializer
from .models import Fleet, ReceivedData, LocationTrackerService, LocationTrackerData


class FleetViewSet(viewsets.ModelViewSet):

    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated, ]
    serializer_class = FleetSerializer
    queryset = Fleet.objects.all()


class ReceivedDataViewSet(viewsets.ModelViewSet):

    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated, ]
    serializer_class = ReceivedDataSerializer
    queryset = ReceivedData.objects.all()


class StoreLocationTrackerData(APIView):

    authentication_classes = [TokenAuthentication, ]
    permission_classes = [IsAuthenticated, ]

    def post(self, request):

        if LocationTrackerService.objects.count() == 0:
            service = LocationTrackerService.objects.create(name="Location Tracker")
        else:
            service = LocationTrackerService.objects.first()

        if service.maintenance:
            return Response({"error": "Server on maintenance"}, status=HTTP_503_SERVICE_UNAVAILABLE)

        data = LocationTrackerData.objects.create(**request.data)
        return Response(
            {
                "id": data.id,
                "owner": data.owner,
                "device": data.device,
                "location": data.location,
                "coords": data.coords,
            }
            , status=HTTP_201_CREATED
        )
