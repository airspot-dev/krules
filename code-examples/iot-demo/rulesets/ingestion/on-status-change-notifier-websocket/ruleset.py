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
    Notify ACTIVE
    """,
    {
        rulename: "on-device-active-notify-websocket",
        subscribe_to: [SUBJECT_PROPERTY_CHANGED],
        ruledata: {
            filters: [
                OnSubjectPropertyChanged("status", "ACTIVE")
            ],
            processing: [
                WebsocketDevicePublishMessage(
                    lambda self: {
                        "id": self.subject.name.split(":")[2],  # subject name format device:<fleet>:<id>
                        "status": self.payload["value"],
                        "event": "Receiving data",
                        "event_class": WebsocketNotificationEventClass.NORMAL,
                    }
                )
            ]
        }
    },
    """
    Notify INACTIVE
    """,
    {
        rulename: "on-device-inactive-notify-websocket",
        subscribe_to: [SUBJECT_PROPERTY_CHANGED],
        ruledata: {
            filters: [
                OnSubjectPropertyChanged("status", "INACTIVE")
            ],
            processing: [
                WebsocketDevicePublishMessage(
                    lambda self: {
                        "id": self.subject.name.split(":")[2], # subject name format device:<fleet>:<id>
                        "status": self.payload["value"],
                        "event": "No more data receiving",
                        "event_class": WebsocketNotificationEventClass.WARNING,
                    }
                )
            ]
        }
    },
]

