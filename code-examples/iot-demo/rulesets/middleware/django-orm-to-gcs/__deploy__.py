
name = "django-orm-to-gcs"

add_files = (
    "ruleset.py",
)

add_modules = True  # find modules in directory (folders having __init__.py file) and add them to container

extra_commands = (
   ("RUN", "pip install google-cloud-storage==1.20.0"),
   ("RUN", "pip install cloudstorage==0.10.0")
)

labels = {
    "serving.knative.dev/visibility": "cluster-local",
    "krules.airspot.dev/type": "ruleset",
    "configs.krules.airspot.dev/google-cloud": "inject"
}

template_annotations = {
    "autoscaling.knative.dev/minScale": "0",
}

#service_account = "my-service-account"

triggers = (
   {
       "name": "django-orm-to-gcs-trigger",
       "filter": {
           "attributes": {
               "djangoapp": "device_manager",
               "djangomodel": "fleet"
           }
       }
   },
)
triggers_default_broker="default"

ksvc_sink = "broker:default"
ksvc_procevents_sink = "broker:procevents"
