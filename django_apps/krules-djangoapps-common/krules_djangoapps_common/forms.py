from django.forms import JSONField


class EmptyObjectJSONField(JSONField):
    empty_values = [None, ""]