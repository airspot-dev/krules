
name = "manage-device-status-set-temp-status"

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
    "krules.airspot.dev/ruleset": name
}

template_annotations = {
    "autoscaling.knative.dev/minScale": "1",
}

#service_account = "my-service-account"

triggers = (
   {
       "name": "class-a-%s-data-received" % name,
       "filter": {
           "attributes": {
               "type": "data-received",
               "phase": "running",
               "subjecttype": "device",
           }
       }
   },
   {
       "name": "class-a-%s-tempc-changed" % name,
       "filter": {
           "attributes": {
               "type": "subject-property-changed",
               "phase": "running",
               "subjecttype": "device",
               "propertyname": "tempc"
           }
       }
   },
)
triggers_default_broker = "class-a"

ksvc_sink = "broker:default"
ksvc_procevents_sink = "broker:procevents"

