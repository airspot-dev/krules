import requests
from krules_core.base_functions import *
from krules_core import RuleConst as Const

from krules_core.providers import proc_events_rx_factory
from krules_env import publish_proc_events_errors, publish_proc_events_all  #, publish_proc_events_filtered
from krules_core.event_types import SUBJECT_PROPERTY_CHANGED

from app_functions.slack import SlackMessage

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
        rulename: "on-device-active-notify-slack",
        subscribe_to: SUBJECT_PROPERTY_CHANGED,
        ruledata: {
            filters: [
                Filter(lambda payload: payload.get("value") == "ACTIVE")
            ],
            processing: [
                SlackMessage(
                    channel="devices_channel",
                    text=lambda self: ":white_check_mark: *{}* >> device *{}* is now *{}*".format(
                        self.subject.name.split(":")[1],
                        self.subject.name.split(":")[2],
                        self.payload.get("value")
                    )
                ),
            ]
        }
    },
    """
    Notify INACTIVE
    """,
    {
        rulename: "on-device-inactive-notify-slack",
        subscribe_to: SUBJECT_PROPERTY_CHANGED,
        ruledata: {
            filters: [
                Filter(lambda payload: payload.get("value") == "INACTIVE")
            ],
            processing: [
                SlackMessage(
                    channel="devices_channel",
                    text=lambda self: ":ballot_box_with_check: *{}* >> device *{}* becomes *{}*".format(
                        self.subject.name.split(":")[1],
                        self.subject.name.split(":")[2],
                        self.payload.get("value")
                    )
                ),
            ]
        }
    },
]

