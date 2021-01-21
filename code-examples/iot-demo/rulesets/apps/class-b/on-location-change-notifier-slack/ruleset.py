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
    Location changed (first location)
    """,
    {
        rulename: "on-location-changed-starting-notify-slack",
        subscribe_to: event_types.SUBJECT_PROPERTY_CHANGED,
        ruledata: {
            filters: [
                PayloadMatchOne("$.old_value", None)  # first time we get a location
            ],
            processing: [
                SlackMessage(
                    channel="devices_channel",
                    text=lambda self: ":triangular_flag_on_post: *{}* >> device *{}* located in {}".format(
                                    self.subject.name.split(":")[1],
                                    self.subject.name.split(":")[2],
                                    self.payload.get("value")
                                )
                ),
            ]
        }
    },

    """
    Location changed (changed from a known location)
    """,
    {
        rulename: "on-location-changed-moving-notify-slack",
        subscribe_to: event_types.SUBJECT_PROPERTY_CHANGED,
        ruledata: {
            filters: [
                PayloadMatchOne("$.old_value", lambda v: v is not None)
            ],
            processing: [
                SlackMessage(
                    channel="device_channel",
                    text=lambda self: ":rocket: *{}* >> device *{}* moved to {}".format(
                                    self.subject.name.split(":")[1],
                                    self.subject.name.split(":")[2],
                                    self.payload.get("value")
                                )
                ),
            ]
        }
    },

]

