
name = "on-temp-status-change-handler"

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
    "krules.airspot.dev/ruleset": name,
    "configs.krules.airspot.dev/django-restapi-consumer": "inject",
}

template_annotations = {
    "autoscaling.knative.dev/minScale": "1",
}

#service_account = "my-service-account"

triggers = (
   {
       "name": "class-a-%s-temp-status-recheck" % name,
       "filter": {
           "attributes": {
               "type": "temp-status-recheck",
               "phase": "running",
               "subjecttype": "device",
           }
       }
   },
   {
       "name": "class-a-%s-prop-change" % name,
       "filter": {
           "attributes": {
               "type": "subject-property-changed",
               "phase": "running",
               "subjecttype": "device",
               "propertyname": "temp_status"
           }
       }
   },
)
triggers_default_broker = "class-a"

ksvc_sink = "broker:default"
ksvc_procevents_sink = "broker:procevents"

