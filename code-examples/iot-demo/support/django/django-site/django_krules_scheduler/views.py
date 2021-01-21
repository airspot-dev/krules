from rest_framework import viewsets, status
from rest_framework.response import Response

from .models import ScheduledEvent
from .serializers import ScheduledEventSerializer
from django.conf import settings
from pydoc import locate


def _evaluate_classes(classes):

    evaluated = []
    for cls in classes:
        if isinstance(cls, str):
            evaluated.append(locate(cls))
        else:
            evaluated.append(cls)
    return evaluated


class ScheduledEventViewSet(viewsets.ModelViewSet):

    authentication_classes = _evaluate_classes(settings.SCHEDULED_EVENTS_AUTHENTICATION_CLASSES)
    permission_classes = _evaluate_classes(settings.SCHEDULED_EVENTS_PERMISSION_CLASSES)
    serializer_class = ScheduledEventSerializer
    queryset = ScheduledEvent.objects.all()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=False)
        if 'uid' in serializer.data:
            query = ScheduledEvent.objects.filter(uid=serializer.data['uid'])
            if query.count() > 0:
                query.update(**serializer.data)
                return Response(serializer.data, status=status.HTTP_200_OK)
        event = ScheduledEvent.objects.create(**serializer.data)
        response = serializer.data
        response["uid"] = event.uid
        headers = self.get_success_headers(serializer.data)
        return Response(response, status=status.HTTP_201_CREATED, headers=headers)

    def get_queryset(self):
        qp = {}
        for key in self.request.query_params.keys():
            qp[key] = self.request.query_params.get(key)
        return ScheduledEvent.objects.filter(**qp)

    # def destroy(self, request, *args, **kwargs):
    #     return super().destroy(request, *args, **kwargs)
