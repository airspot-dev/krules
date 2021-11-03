from django.db.models import Q
from django.contrib import admin


class DeepSearchModelAdmin(admin.ModelAdmin):
    deep_search_fields = ()

    def get_search_results(self, request, queryset, search_term):

        deep_filtered_queryset = None
        default_queryset, use_distinct = super(DeepSearchModelAdmin, self).get_search_results(request, queryset,
                                                                                              search_term)
        if len(default_queryset) == 0 and len(self.deep_search_fields) > 0:
            search_term = search_term.replace(" ", "").replace("\"", "").replace("'", "")
            items = search_term.split(",")
            for i in items:
                if deep_filtered_queryset is None:
                    qs = queryset
                else:
                    qs = deep_filtered_queryset
                try:
                    k, v = i.split(":")
                    deep_filtered_queryset = qs.filter(self._get_deep_filters(k, v))
                    if len(deep_filtered_queryset) == 0:
                        break
                except ValueError:
                    continue
        return deep_filtered_queryset or default_queryset, use_distinct

    def _get_deep_filters(self, key, value):
        filters = None
        for f in self.deep_search_fields:
            # value get from search_term is a string so we check also the evaluated value
            if filters is None:
                filters = Q(**{"%s__%s" % (f, key): value}) | Q(**{"%s__%s" % (f, key): eval(value)})
            else:
                filters = filters | Q(**{"%s__%s" % (f, key): value}) | Q(**{"%s__%s" % (f, key): eval(value)})

        return filters