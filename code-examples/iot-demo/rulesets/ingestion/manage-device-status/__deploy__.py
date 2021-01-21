
name = "manage-device-status"

add_files = (
    "ruleset.py",
)

add_modules = True  # find modules in directory (folders having __init__.py file) and add them to container

extra_commands = (
#    ("RUN", "pip install my-wonderful-lib==1.0")
)

labels = {
    "serving.knative.dev/visibility": "cluster-local",
    "krules.airspot.dev/type": "ruleset",
    "configs.krules.airspot.dev/django-restapi-consumer": "inject",
    "krules.airspot.dev/ruleset": name
}

template_annotations = {
    "autoscaling.knative.dev/minScale": "1",
}

#service_account = "my-service-account"

triggers = (
   {
       "name": name,
       "broker": "data-received",
   },
   {
       "name": f"{name}-prop-changes",
       "filter": {
           "attributes": {
               "type": "subject-property-changed",
               "phase": "running",  # avoid onboarding props, becames running after first data are received
           }
       }
   },
   {
       "name": "%s-request-device-status" % name,
       "filter": {
           "attributes": {
               "type": "request-device-status",
           }
       },
   }
)
triggers_default_broker = "default"

ksvc_sink = "broker:default"
ksvc_procevents_sink = "broker:procevents"

