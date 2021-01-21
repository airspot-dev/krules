
name = "on-temp-status-change-notifier-slack"

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
    "configs.krules.airspot.dev/slack-webhooks": "inject"
}

template_annotations = {
    "autoscaling.knative.dev/minScale": "1",
}

#service_account = "my-service-account"

triggers = (
   {
       "name": "class-a-%s-back-to-normal" % name,
       "filter": {
           "attributes": {
               "type": "temp-status-back-to-normal"
           }
       }
   },
   {
       "name": "class-a-%s-status-bad" % name,
       "filter": {
           "attributes": {
               "type": "temp-status-bad"
           }
       }
   },
   {
       "name": "class-a-%s-status-still-bad" % name,
       "filter": {
           "attributes": {
               "type": "temp-status-still-bad"
           }
       }
   },
)
triggers_default_broker = "class-a"

ksvc_sink = "broker:default"
ksvc_procevents_sink = "broker:procevents"

