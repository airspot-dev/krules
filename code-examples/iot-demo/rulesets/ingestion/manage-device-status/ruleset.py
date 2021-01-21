from krules_core.base_functions import *
from krules_core import RuleConst as Const
from datetime import datetime, timezone, timedelta
from app_functions import *
from uuid import uuid4

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

from krules_core.providers import proc_events_rx_factory
from krules_env import publish_proc_events_errors, publish_proc_events_all  # , publish_proc_events_filtered
from krules_core.event_types import SUBJECT_PROPERTY_CHANGED

# proc_events_rx_factory().subscribe(
#   on_next=publish_proc_events_all,
# )
proc_events_rx_factory().subscribe(
    on_next=publish_proc_events_errors,
)


rulesdata = [

    """
    On data received we just set a "lastSeen" property allowing reacting for changing status
    """,
    {
        rulename: "manage-device-status-set-lastseen",
        subscribe_to: "data-received",
        ruledata: {
            processing: [
                SetSubjectProperty("lastSeen", lambda: datetime.now(timezone.utc).isoformat()),
            ]
        }
    },
    """
    When a subject property (except for status) changes, sets status to active
    """,
    {
        rulename: "on-property-update-set-status-active",
        subscribe_to: [SUBJECT_PROPERTY_CHANGED],
        ruledata: {
            filters: [
                Filter(lambda payload: payload["property_name"] != "status")
            ],
            processing: [
                SetSubjectProperty("status", "ACTIVE", use_cache=False),
                Schedule(
                    key="schedule_status_uid",
                    event_type="request-device-status",
                    payload={
                        "value": "INACTIVE"
                    },
                    when=lambda subject: datetime.now(timezone.utc) + timedelta(
                            seconds=int(subject.rate)),
                ),
            ]
        }
    },

    """
    Set device status, used to set INACTIVE by the scheduler
    """,
    {
        rulename: 'on-request-device-status',
        subscribe_to: "request-device-status",
        ruledata: {
            processing: [
                SetSubjectProperty("status", lambda payload: payload["value"])
            ]
        }
    },

    """
    Since we have already intercepted the subject property changed event inside the container we need to send it out 
    explicitly
    """,
    {
        rulename: "device-status-propagate",
        subscribe_to: SUBJECT_PROPERTY_CHANGED,
        ruledata: {
            filters: [
                Filter(lambda payload: payload["property_name"] == "status")
            ],
            processing: [
                Route(dispatch_policy=DispatchPolicyConst.DIRECT)
            ]
        },
    },
]
