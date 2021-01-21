import requests
from krules_core.base_functions import *
from krules_core import RuleConst as Const, event_types

from krules_core.providers import proc_events_rx_factory
from krules_env import publish_proc_events_errors, publish_proc_events_all  #, publish_proc_events_filtered

from app_functions.slack import SlackMessage

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
    Notify middleware service
    """,
    {
        rulename: "on-url-changed-notify-slack",
        subscribe_to: [event_types.SUBJECT_PROPERTY_CHANGED],
        ruledata: {
            filters: [
                SubjectNameMatch("ksvc:(?P<app>.+):(?P<fleet>.+)"),
            ],
            processing: [
                PrepareSlackTextMessage(payload_dest="text"),
                SlackMessage(
                    channel="middleware_channel",
                    text=lambda payload: payload["text"]
                ),
            ]
        }
    },
    # more rules here..
]

