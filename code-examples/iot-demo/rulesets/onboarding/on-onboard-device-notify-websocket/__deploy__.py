
name = "on-onboard-device-notify-websocket"

add_files = (
    "ruleset.py",
)

add_modules = True  # find modules in directory (folders having __init__.py file) and add them to container

extra_commands = (
    ("RUN", "apk add libffi-dev "),
    ("RUN", "apk add openssl-dev"),
    ("RUN", "pip3 install pusher==3.0.0"),
)

labels = {
    "serving.knative.dev/visibility": "cluster-local",
    "krules.airspot.dev/type": "ruleset",
    "krules.airspot.dev/ruleset": name,
    "configs.krules.airspot.dev/pusher": "inject"
}

template_annotations = {
    "autoscaling.knative.dev/minScale": "1",
}

#service_account = "my-service-account"

triggers = (
   {
       "name": name,
       "filter": {
           "attributes": {
               "phase": "onboarded",
               "type": "subject-property-changed",
               "propertyname": "status"
           }
       }
   },
)
triggers_default_broker="default"

ksvc_sink = "broker:default"
ksvc_procevents_sink = "broker:procevents"

