
name = "django-orm-to-k8s"

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
    "autoscaling.knative.dev/minScale": "0",
}

service_account = "demo-serviceaccount"

triggers = (
   {
       "name": "django-orm-to-k8s-fleet-post-save",
       "filter": {
           "attributes": {
               "type": "django.orm.post_save",
               "djangoapp": "device_manager",
               "djangomodel": "fleet"
           }
       }
   },
   {
       "name": "django-orm-to-k8s-fleet-post-delete",
       "filter": {
           "attributes": {
               "type": "django.orm.post_delete",
               "djangoapp": "device_manager",
               "djangomodel": "fleet"
           }
       }
   },
)
triggers_default_broker = "default"

ksvc_sink = "broker:default"
ksvc_procevents_sink = "broker:procevents"

