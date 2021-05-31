from django.db.models import JSONField


class EmptyObjectJSONField(JSONField):
    empty_values = [None, ""]

    def formfield(self, **kwargs):
        from .forms import EmptyObjectJSONField

        return super().formfield(**{"form_class": EmptyObjectJSONField, **kwargs})