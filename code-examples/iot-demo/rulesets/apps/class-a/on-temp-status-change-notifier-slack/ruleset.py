import requests

from krules_core.base_functions import *
from krules_core import RuleConst as Const

from krules_core.providers import proc_events_rx_factory
from krules_env import publish_proc_events_errors, publish_proc_events_all  # , publish_proc_events_filtered

from app_functions import SlackMessage

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

# proc_events_rx_factory().subscribe(
#   on_next=publish_proc_events_all,
# )
proc_events_rx_factory().subscribe(
    on_next=publish_proc_events_errors,
)

rulesdata = [
    """
    On status back to NORMAL notify
    """,
    {
        rulename: "on-temp-status-back-to-normal-slack-notifier",
        subscribe_to: "temp-status-back-to-normal",
        ruledata: {
            processing: [
                SlackMessage(
                    channel="devices_channel",
                    text=lambda subject: ":sunglasses: *{}* >> device *{}* temp status back to normal! ".format(
                                subject.name.split(":")[1],
                                subject.name.split(":")[2],
                            )
                ),
            ],
        },
    },

    """
    Status COLD or OVERHEATED
    """,
    {
        rulename: "on-temp-status-bad-slack-notifier",
        subscribe_to: "temp-status-bad",
        ruledata: {
            processing: [
                SlackMessage(
                    channel="devices_channel",
                    text=lambda self: ":scream: *{}* >> device *{}* is *{}* ({}°C)".format(
                                self.subject.name.split(":")[1],
                                self.subject.name.split(":")[2],
                                self.payload.get("status"),
                                self.payload.get("tempc")
                            )
                ),
            ],
        },
    },

    """
    Notify device status is still bad 
    """,
    {
        rulename: "on-temp-status-recheck-slack-notifier",
        subscribe_to: "temp-status-still-bad",
        ruledata: {
            processing: [
                SlackMessage(
                    channel="devices_channel",
                    text=lambda self: ":neutral_face: *{}* >> device *{}* is still *{}* from {} secs".format(
                                self.subject.name.split(":")[1],
                                self.subject.name.split(":")[2],
                                self.payload.get("status"),
                                self.payload.get("seconds")
                            )
                ),
            ],
        },
    },
]
