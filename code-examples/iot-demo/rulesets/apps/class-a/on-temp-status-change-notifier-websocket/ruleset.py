from app_functions.pusherclient import WebsocketNotificationEventClass, WebsocketDevicePublishMessage
from krules_core.base_functions import *
from krules_core import RuleConst as Const
from krules_core.event_types import SUBJECT_PROPERTY_CHANGED

from krules_core.providers import proc_events_rx_factory
from krules_env import publish_proc_events_errors, publish_proc_events_all  # , publish_proc_events_filtered

# try:
#     from ruleset_functions import *
# except ImportError:
#     # for local development
#     from .ruleset_functions import *


rulename = Const.RULENAME
subscribe_to = Const.SUBSCRIBE_TO
ruledata = Const.RULEDATA
filters = Const.FILTERS
processing = Const.PROCESSING

DEVICE_DATA = "device-data"

# proc_events_rx_factory().subscribe(
#   on_next=publish_proc_events_all,
# )
proc_events_rx_factory().subscribe(
    on_next=publish_proc_events_errors,
)

rulesdata = [
    """
    Send new tempc value to websocket
    """,
    {
        rulename: "on-tempc-changed-websocket-notifier",
        subscribe_to: SUBJECT_PROPERTY_CHANGED,
        ruledata: {
            processing: [
                WebsocketDevicePublishMessage(
                    lambda self: {
                        "id": self.subject.name.split(":")[2],
                        "value": self.payload.get("value")
                    }
                ),
            ]
        }
    },

    """
    On status NORMAL notify
    """,
    {
        rulename: "on-temp-status-back-to-normal-websocket-notifier",
        subscribe_to: "temp-status-back-to-normal",
        ruledata: {
            processing: [
                WebsocketDevicePublishMessage(
                    lambda subject: {
                        "id": subject.name.split(":")[2],
                        "event": "Temp status back to normal! ",
                        "event_class": WebsocketNotificationEventClass.NORMAL,
                    }
                ),
            ],
        },
    },

    """
    Status COLD or OVERHEATED
    """,
    {
        rulename: "on-temp-status-bad-websocket-notifier",
        subscribe_to: "temp-status-bad",
        ruledata: {
            processing: [
                WebsocketDevicePublishMessage(
                    lambda self: {
                        "id": self.subject.name.split(":")[2],
                        "event": "*{}* ({}°C)".format(
                            self.payload.get("status"), self.subject.get("tempc")
                        ),
                        "event_class": WebsocketNotificationEventClass.WARNING,
                    }
                ),
            ],
        },
    },

    """
    Recheck
    """,
    {
        rulename: "on-temp-status-recheck-websocket-notifier",
        subscribe_to: "temp-status-still-bad",
        ruledata: {
            processing: [
                WebsocketDevicePublishMessage(
                    lambda self: {
                        "id": self.subject.name.split(":")[2],
                        "event": "...still *{}* from {} secs".format(
                            self.payload.get("status"),
                            self.payload.get("seconds"),
                        ),
                        "event_class": WebsocketNotificationEventClass.CRITICAL,
                    }),
            ],
        },
    },
]
