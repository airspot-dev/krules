
name = "on-location-change-notifier-postextapi"

add_files = (
    "ruleset.py",
)

add_modules = True  # find modules in directory (folders having __init__.py file) and add them to container

extra_commands = (
#    ("RUN", "pip install my-wonderful-lib==1.0"),
)

labels = {
    "serving.knative.dev/visibility": "cluster-local",
    "krules.airspot.dev/type": "ruleset",
    "krules.airspot.dev/ruleset": name,
    "configs.krules.airspot.dev/django-restapi-consumer": "inject",
}

template_annotations = {
    "autoscaling.knative.dev/minScale": "1",
}

#service_account = "my-service-account"

triggers = (
    {
        "name": f"{name}-location-changed",
        "filter": {
            "attributes": {
                "type": "subject-property-changed",
                "propertyname": "location",
            }
        }
    },
    {
        "name": f"{name}-on-error",
        "filter": {
            "attributes": {
                "type": "on-location-change-notifier-postextapi-errors",
            }
        }
    },
    {
        "name": f"{name}-do-extapi-post",
        "filter": {
            "attributes": {
                "type": "do-extapi-post",
            }
        }
    },
)
triggers_default_broker = "default"

ksvc_sink = "broker:default"
ksvc_procevents_sink = "broker:procevents"

