from app_functions.restapiclient import DoDeleteApiCall
from krules_core.base_functions import *
from krules_core import RuleConst as Const

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

from krules_core.providers import proc_events_rx_factory, subject_factory
from krules_env import publish_proc_events_errors, publish_proc_events_all, publish_proc_events_filtered

# proc_events_rx_factory().subscribe(
#     on_next=publish_proc_events_all,
# )
proc_events_rx_factory().subscribe(
    on_next=publish_proc_events_errors,
)

rulesdata = [
    """
    On tick route scheduled events
    """,
    {
        rulename: "on-tick-do-schedules",
        subscribe_to: "krules.heartbeat",
        ruledata: {
            processing: [
                DispatchScheduledEvents()
            ]
        }
    },

    """
    """,
    {
        rulename: "on-dispatch-event-delete-schedule",
        subscribe_to: "dispatch-event",
        ruledata: {
            processing: [
                Route(
                    event_type=lambda payload: payload["event_type"],
                    subject=lambda payload: payload["subject"],
                    payload=lambda payload: payload["payload"],
                ),
                DoDeleteApiCall(
                    path=lambda payload: "/scheduler/scheduled_event/%s" % payload["uid"],
                )
            ]
        }
    },
]
