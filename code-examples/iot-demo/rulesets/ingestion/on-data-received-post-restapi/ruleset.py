
from krules_core.base_functions import *
from krules_core import RuleConst as Const

from datetime import datetime, timezone
import requests

rulename = Const.RULENAME
subscribe_to = Const.SUBSCRIBE_TO
ruledata = Const.RULEDATA
filters = Const.FILTERS
processing = Const.PROCESSING

from krules_core.providers import proc_events_rx_factory
from krules_env import publish_proc_events_errors, publish_proc_events_all  #, publish_proc_events_filtered

from app_functions.restapiclient import DoPostApiCall

# try:
#     from ruleset_functions import *
# except ImportError:
#     # for local development
#     from .ruleset_functions import *
    
# proc_events_rx_factory().subscribe(
#   on_next=publish_proc_events_all,
# )
proc_events_rx_factory().subscribe(
 on_next=publish_proc_events_errors,
)

rulesdata = [
    """
    When receive a new device data post it to Rest API
    """,
    {
        rulename: "manage-device-status-post-restapi",
        subscribe_to: ["data-received"],
        ruledata: {
            filters: [
                SubjectNameMatch("device:(?P<owner>.+):(?P<devicename>.+)", payload_dest="device_info")
            ],
            processing: [
                DoPostApiCall(
                    path="/device_manager/received_data/",
                    json=lambda self: {
                        "owner": self.payload["device_info"]["owner"],
                        "device": self.payload["device_info"]["devicename"],
                        "timestamp": self.payload["receivedAt"],
                        "data": self.payload["data"],
                    },
                ),
            ]
        }
    },
]

