from django.contrib import admin
from django.db.models import JSONField
from django_krules_procevents.widgets import ReadOnlyJSONWidget

from .models import Fleet, ReceivedData, LocationTrackerService, LocationTrackerData


@admin.register(Fleet)
class FleetAdmin(admin.ModelAdmin):
    readonly_fields = ["endpoint", "dashboard"]


@admin.register(ReceivedData)
class ReceivedDataAdmin(admin.ModelAdmin):
    list_display = ['owner', 'device', 'timestamp']
    search_fields = ['device']
    list_filter = ['owner']
    readonly_fields = ['device', 'owner', 'timestamp']
    formfield_overrides = {
        JSONField: {'widget': ReadOnlyJSONWidget()},
    }

    def has_add_permission(self, request):
        return False


@admin.register(LocationTrackerService)
class LocationTrackerServiceAdmin(admin.ModelAdmin):
    list_display = ["name", "maintenance"]
    list_editable = ["maintenance"]

    def has_add_permission(self, request):
        return False


@admin.register(LocationTrackerData)
class LocationTrackerServiceAdmin(admin.ModelAdmin):
    list_display = ["owner", "device", "location", "coords", "timestamp"]
    readonly_fields = ["owner", "device", "location", "coords", "timestamp"]
    search_fields = ["owner", "device"]
    list_filter = ["owner", "device"]

    def has_add_permission(self, request):
        return False
