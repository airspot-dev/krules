
from krules_core.base_functions import *
from krules_core import RuleConst as Const, event_types

from krules_core.providers import proc_events_rx_factory
from krules_env import publish_proc_events_errors, publish_proc_events_all  #, publish_proc_events_filtered

from app_functions.pusherclient import WebsocketNotificationEventClass, WebsocketDevicePublishMessage

try:
    from ruleset_functions import *
except ImportError:
    # for local development
    from .ruleset_functions import *


rulename = Const.RULENAME
subscribe_to = Const.SUBSCRIBE_TO
ruledata = Const.RULEDATA
filters = Const.FILTERS
processing = Const.PROCESSING


proc_events_rx_factory().subscribe(
  on_next=publish_proc_events_all,
)
# proc_events_rx_factory().subscribe(
#  on_next=publish_proc_events_errors,
# )

rulesdata = [
    """
     Send all coords variations
     """,
    {
        rulename: "on-coords-changed-notify-websocket",
        subscribe_to: event_types.SUBJECT_PROPERTY_CHANGED,
        ruledata: {
            filters: [
                OnSubjectPropertyChanged("coords"),
            ],
            processing: [
                WebsocketDevicePublishMessage(
                    lambda self: {
                        "id": self.subject.name.split(":")[2],
                        "value": self.payload["value"]
                    }
                ),
            ]
        }
    },

    """
    Send location (cheering)
    """,
    {
        rulename: "on-location-changed-notify-websocket-cheering",
        subscribe_to: event_types.SUBJECT_PROPERTY_CHANGED,
        ruledata: {
            filters: [
                OnSubjectPropertyChanged("location"),
                PayloadMatchOne("$.old_value", None)
            ],
            processing: [
                WebsocketDevicePublishMessage(
                    lambda self: {
                        "id": self.subject.name.split(":")[2],
                        "event": self.payload["value"],
                        "event_class": WebsocketNotificationEventClass.CHEERING,
                    }
                ),
            ]
        }
    },

    """
    Send location (normal)
    """,
    {
        rulename: "on-location-changed-notify-websocket-normal",
        subscribe_to: event_types.SUBJECT_PROPERTY_CHANGED,
        ruledata: {
            filters: [
                OnSubjectPropertyChanged("location"),
                PayloadMatchOne("$.old_value", lambda v: v is not None)
            ],
            processing: [
                WebsocketDevicePublishMessage(
                    lambda self: {
                        "id": self.subject.name.split(":")[2],
                        "event": self.payload["value"],
                        "event_class": WebsocketNotificationEventClass.NORMAL,
                    }
                ),
            ]
        }
    },
]

