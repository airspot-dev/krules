
from krules_core.base_functions import *
from krules_core import RuleConst as Const

rulename = Const.RULENAME
subscribe_to = Const.SUBSCRIBE_TO
ruledata = Const.RULEDATA
filters = Const.FILTERS
processing = Const.PROCESSING

from krules_core.route.router import DispatchPolicyConst
from krules_env import RULE_PROC_EVENT
from krules_core.providers import proc_events_rx_factory
import pprint
proc_events_rx_factory().subscribe(
  on_next=pprint.pprint,
)

rulesdata = [
    """
    On error propagate it to service which produced it.
    """,
    {
        rulename: "on-procevents-error-propagate",
        subscribe_to: [RULE_PROC_EVENT],
        ruledata: {
            filters: [
                Filter(lambda payload: payload["got_errors"])
            ],
            processing: [
                Route(
                    event_type=lambda subject: "{}-errors".format(subject.event_info()["source"]),
                    subject=lambda payload: payload["subject"],
                    payload=lambda payload: payload,
                    dispatch_policy=DispatchPolicyConst.DIRECT
                )
            ]
        }
    },
]

