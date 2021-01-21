from cloudstorage.drivers.google import GoogleStorageDriver

from krules_core.base_functions import *
from krules_core import RuleConst as Const
import os

rulename = Const.RULENAME
subscribe_to = Const.SUBSCRIBE_TO
ruledata = Const.RULEDATA
filters = Const.FILTERS
processing = Const.PROCESSING

from krules_core.providers import proc_events_rx_factory, subject_factory
from krules_env import publish_proc_events_errors, publish_proc_events_all  #, publish_proc_events_filtered

from ruleset_functions import ProcessCSVAsDict, DeleteBlob
    
# proc_events_rx_factory().subscribe(
#   on_next=publish_proc_events_all,
# )

proc_events_rx_factory().subscribe(
 on_next=publish_proc_events_errors,
)

# google credentials are stored in the configurations provider
# rather then in its own secret mounted as a volume
# so we write it down in a file when the container is ready
with open("google-cloud-key.json", "w") as f:
    f.write(configs_factory()["google-cloud"]["credentials"]["key.json"])
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.abspath(f.name)

rulesdata = [
    """
    Subscribe to storage import csv event and dispatch device_data event for each record
    """,
    {
        rulename: "on-csv-upload-import-devices",
        subscribe_to: "google.cloud.storage.object.v1.finalized",
        ruledata: {
            filters: [
                SubjectNameMatch(
                    "objects/(?P<fleetname>.+)/import/(?P<deviceclass>.+)/(?P<filename>.+)",
                    payload_dest="path_info"
                )
            ],
            processing: [
                ProcessCSVAsDict(
                    driver=GoogleStorageDriver,
                    bucket=lambda payload: payload["bucket"],
                    path=lambda payload: payload["name"],
                    func=lambda device_data, self: (
                        self.router.route(
                            event_type="onboard-device",
                            subject=subject_factory(
                                "device:%s:%s" % (self.payload["path_info"]["fleetname"], device_data.pop("deviceid"))
                            ),
                            payload={
                                "data": device_data,
                                "class": self.payload["path_info"]["deviceclass"],
                                "fleet": self.payload["path_info"]["fleetname"],
                            }
                        ),
                    )
                )
            ]
        }
    },

    """
    If processed csv is malformed and generate an error delete it from bucket 
    """,
    {
        rulename: 'on-csv-upload-import-devices-error',
        subscribe_to: "on-gcs-csv-upload-errors",
        ruledata: {
            filters: [
                PayloadMatchOne("$.name", "on-csv-upload-import-devices")
            ],
            processing: [
                DeleteBlob(
                    driver=GoogleStorageDriver,
                    bucket=lambda payload: payload["payload"]["bucket"],
                    path=lambda payload: payload["payload"]["name"]
                )
            ]

        }
    },
]

