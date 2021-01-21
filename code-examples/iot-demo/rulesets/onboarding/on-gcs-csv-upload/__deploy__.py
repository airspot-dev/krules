
name = "on-gcs-csv-upload"

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
    "krules.airspot.dev/ruleset": name,
    "configs.krules.airspot.dev/google-cloud": "inject"
}

template_annotations = {
    "autoscaling.knative.dev/minScale": "1",
}

#service_account = "my-service-account"

triggers = (
   {
       "name": "on-gcs-csv-upload-errors",
       "broker": "default",
       "filter": {
           "attributes": {
               "type": "on-gcs-csv-upload-errors"
           }
       }
   },
)

triggers_default_broker = "default"

ksvc_sink = "broker:default"
ksvc_procevents_sink = "broker:procevents"

