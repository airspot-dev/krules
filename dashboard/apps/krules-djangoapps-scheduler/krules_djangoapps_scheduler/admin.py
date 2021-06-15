from django.contrib import admin

from .models import ScheduledEvent, SchedulerConfig
from krules_djangoapps_common.admin import DeepSearchModelAdmin
from krules_djangoapps_common.fields import EmptyObjectJSONField
from jsoneditor.forms import JSONEditor


@admin.register(ScheduledEvent)
class ScheduledEventAdmin(DeepSearchModelAdmin):
    search_fields = ("origin_id", "subject", "event_type")
    deep_search_fields = ("payload",)
    list_filter = ("event_type",)
    fields = ('uid', 'event_type', 'subject', 'subject_key', 'payload', 'origin_id', 'when')
    readonly_fields = ('uid',)
    formfield_overrides = {
        EmptyObjectJSONField: {'widget': JSONEditor},
    }
    list_display = ['uid', 'event_type', 'subject', 'subject_key', 'when']


@admin.register(SchedulerConfig)
class SchedulerConfigAdmin(admin.ModelAdmin):
    list_display = ("period",)
    list_editable = ("period",)
    list_display_links = None

    def has_add_permission(self, request):
        if super().has_add_permission(request):
            return SchedulerConfig.objects.count() == 0
        return False

    def has_delete_permission(self, request, obj=None):
        if super().has_delete_permission(request, obj):
            return SchedulerConfig.objects.count() > 1
        return False
