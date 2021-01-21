from app_functions.pusherclient import WebsocketNotificationEventClass, WebsocketDevicePublishMessage
from krules_core.base_functions import *
from krules_core import RuleConst as Const
from krules_core.event_types import SUBJECT_PROPERTY_CHANGED

from krules_core.providers import proc_events_rx_factory
from krules_env import publish_proc_events_errors, publish_proc_events_all  #, publish_proc_events_filtered


rulename = Const.RULENAME
subscribe_to = Const.SUBSCRIBE_TO
ruledata = Const.RULEDATA
filters = Const.FILTERS
processing = Const.PROCESSING

# proc_events_rx_factory().subscribe(
#   on_next=publish_proc_events_all,
# )
proc_events_rx_factory().subscribe(
 on_next=publish_proc_events_errors,
)

rulesdata = [
    """
    Notify onboarded (READY)
    """,
    {
        rulename: "on-device-ready-notify-websocket",
        subscribe_to: [SUBJECT_PROPERTY_CHANGED],
        ruledata: {
            filters: [
                Filter(lambda payload: payload.get("value") == "READY")
            ],
            processing: [
                WebsocketDevicePublishMessage(
                    lambda self:{
                        "id": self.subject.name.split(":")[2],  # subject name format device:<fleet>:<id>
                        "device_class": self.payload["_event_info"]["deviceclass"],
                        "status": self.payload["value"],
                        "event": "Onboarded",
                        "event_class": WebsocketNotificationEventClass.CHEERING,
                    }
                )
            ]
        }
    },
]

