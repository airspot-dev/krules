from django.contrib import admin
from django.contrib.postgres.fields import JSONField
from django_json_widget.widgets import JSONEditorWidget
from prettyjson import PrettyJSONWidget


from .models import Service, Configuration


class ConfigurationInline(admin.TabularInline):
    model = Configuration
    fields = ("image", "env", "traffic")
    readonly_fields = ("image", "env")
    extra = 0


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    fields = ('name', 'image', 't_version')
    inlines = (ConfigurationInline, )


@admin.register(Configuration)
class ConfigurationAdmin(admin.ModelAdmin):
    list_display = ("name", "image", "traffic")
    list_editable = ("traffic", )
    readonly_fields = ("name", "image")
    formfield_overrides = {
        JSONField: {'widget': PrettyJSONWidget(attrs={'initial': 'parsed'})},
    }
