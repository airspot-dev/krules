from django.contrib import admin
from krules_djangoapps_common.admin import DeepSearchModelAdmin
from krules_djangoapps_common.fields import EmptyObjectJSONField
from krules_djangoapps_common.widgets import ReadOnlyJSONWidget

from .models import ProcessingEvent


@admin.register(ProcessingEvent)
class ProcessingEventAdmin(DeepSearchModelAdmin):
    search_fields = ("origin_id", "subject", "source")
    deep_search_fields = ("payload", "event_info")
    list_filter = ("passed", "got_errors", "rule_name", "type", "source")
    fields = ("rule_name", "type", "subject", "success", "passed", "origin_id", "time", "event_info", "payload",
              "filters", "processing", "source")
    readonly_fields = ("rule_name", "type", "subject", "success", "passed", "origin_id", "time", "source")
    formfield_overrides = {
        EmptyObjectJSONField: {'widget': ReadOnlyJSONWidget()},
    }

    list_display = ["rule_name", "subject", "time", "type", "origin_id", "passed", "success", "source"]

    def success(self, obj):
        return not obj.got_errors

    success.boolean = True

    def has_add_permission(self, request, obj=None):
        return False