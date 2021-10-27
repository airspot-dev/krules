from django.forms import widgets
from prettyjson import PrettyJSONWidget


class ReadOnlyJSONWidget(PrettyJSONWidget):

    def __init__(self, attrs=None):
        if attrs is None:
            attrs = {}
        attrs["initial"] = "parsed"
        super(ReadOnlyJSONWidget, self).__init__(attrs)

    @property
    def media(self):
        widget_media = super(ReadOnlyJSONWidget, self).media
        js = widget_media._js
        js.append('krules/prettyjson.js')
        return widgets.Media(
            js=tuple(js),
            css=widget_media._css,
        )
