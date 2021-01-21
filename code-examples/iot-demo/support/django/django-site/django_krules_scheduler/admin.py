from django.contrib import admin
from django.contrib.postgres.fields import JSONField

from .models import ScheduledEvent
from django.db.models import Q

from .widgets import ReadOnlyJSONWidget


@admin.register(ScheduledEvent)
class ScheduledEventAdmin(admin.ModelAdmin):
    search_fields = ("origin_id", "subject", "event_type")
    list_filter = ("event_type", )
    fields = ('uid', 'event_type', 'subject', 'payload', 'origin_id', 'when')
    readonly_fields = ('uid', 'event_type', 'subject', 'origin_id', 'when')
    formfield_overrides = {
        JSONField: {'widget': ReadOnlyJSONWidget()},
    }
    list_display = ['uid', 'event_type', 'subject', 'payload', 'origin_id', 'when']

    def get_search_results(self, request, queryset, search_term):
        filtered_queryset, use_distinct = super(ScheduledEventAdmin, self).get_search_results(request, queryset,
                                                                                              search_term)
        if len(filtered_queryset) == 0:
            filtered_queryset = queryset
            search_term = search_term.replace(" ", "").replace("\"", "").replace("'", "")
            items = search_term.split(",")
            for i in items:
                try:
                    k, v = i.split(":")
                    filtered_queryset = filtered_queryset.filter(Q(**{"payload__%s" % k: v}))
                    if len(filtered_queryset):
                        break
                except ValueError:
                    continue
        return filtered_queryset, use_distinct
