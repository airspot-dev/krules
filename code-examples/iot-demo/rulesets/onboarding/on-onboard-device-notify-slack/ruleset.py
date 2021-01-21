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


proc_events_rx_factory().subscribe(
  on_next=publish_proc_events_all,
)
# proc_events_rx_factory().subscribe(
#  on_next=publish_proc_events_errors,
# )

rulesdata = [
    """
    Notify onboarded (READY)
    """,
    {
        rulename: "on-device-ready-notify-slack",
        subscribe_to: SUBJECT_PROPERTY_CHANGED,
        ruledata: {
            filters: [
                OnSubjectPropertyChanged("status", "READY"),
            ],
            processing: [
                SlackMessage(
                    channel="devices_channel",
                    text=lambda subject: ":+1: *{}* >> device *{}* on board! ".format(
                                    subject.name.split(":")[1],
                                    subject.name.split(":")[2],
                                )
                )
            ]
        }
    },
]

