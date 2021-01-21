
from krules_core.base_functions import *
from krules_core import RuleConst as Const
import os

rulename = Const.RULENAME
subscribe_to = Const.SUBSCRIBE_TO
ruledata = Const.RULEDATA
filters = Const.FILTERS
processing = Const.PROCESSING

from krules_core.providers import proc_events_rx_factory, configs_factory
from krules_env import publish_proc_events_all

from ruleset_functions import CreateGCSFolder, DeleteGCSFolder

proc_events_rx_factory().subscribe(
  on_next=publish_proc_events_all,
)

# google credentials are stored in the configurations provider
# rather then in its own secret mounted as a volume
# so we write it down in a file when the container is ready
with open("google-cloud-key.json", "w") as f:
    f.write(configs_factory()["google-cloud"]["credentials"]["key.json"])
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.abspath(f.name)

rulesdata = [
    """
    On Fleet model creation create GCS bucket folders 
    """,
    {
        rulename: "on-fleet-model-creation-create-gcs-folders",
        subscribe_to: ["django.orm.post_save"],
        ruledata: {
            filters: [
                Filter(
                    lambda payload:
                        payload["signal_kwargs"]["created"]
                )
            ],
            processing: [
                CreateGCSFolder(
                    bucket="iot-demo-01",
                    path=lambda payload: "%s/import/class-a/" % payload["data"]["name"]
                ),
                CreateGCSFolder(
                    bucket="iot-demo-01",
                    path=lambda payload: "%s/import/class-b/" % payload["data"]["name"]
                ),
            ]
        }
    },

    """
    On Fleet model deletion delete GCS bucket folders 
    """,
    {
        rulename: "on-fleet-model-deletion-delete-gcs-folders",
        subscribe_to: ["django.orm.post_delete"],
        ruledata: {
            filters: [],
            processing: [
                DeleteGCSFolder(
                    bucket="iot-demo-01",
                    path=lambda payload: "%s/" % payload["data"]["name"]
                )
            ]
        }
    },
]

