from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FleetViewSet, ReceivedDataViewSet, StoreLocationTrackerData

# Create a router and register our viewsets with it.
router = DefaultRouter()
router.register(r'fleet', FleetViewSet)
router.register(r'received_data', ReceivedDataViewSet)

# The API URLs are now determined automatically by the router.
urlpatterns = [
    path('', include(router.urls)),
    path('location_tracker', StoreLocationTrackerData.as_view()),
]
