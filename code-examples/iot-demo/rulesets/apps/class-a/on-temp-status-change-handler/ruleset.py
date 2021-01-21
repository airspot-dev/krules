from uuid import uuid4

from dateutil.parser import parse

from app_functions import Schedule
from app_functions.restapiclient import DoPostApiCall
from krules_core.base_functions import *
from krules_core import RuleConst as Const

from krules_core.providers import proc_events_rx_factory
from krules_core.event_types import SUBJECT_PROPERTY_CHANGED
from krules_env import publish_proc_events_errors, publish_proc_events_all  #, publish_proc_events_filtered
from datetime import datetime, timedelta, timezone

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
    On status back to NORMAL
    """,
    {
        rulename: "on-temp-status-back-to-normal",
        subscribe_to: SUBJECT_PROPERTY_CHANGED,
        ruledata: {
            filters: [
                OnSubjectPropertyChanged("temp_status", value="NORMAL", old_value=lambda value: value is not None),
            ],
            processing: [
                Route(event_type="temp-status-back-to-normal",
                      dispatch_policy=DispatchPolicyConst.DIRECT),
                SetSubjectProperty("lastTempStatusChanged", lambda: datetime.now().isoformat(), muted=True)
            ],
        },
    },

    """
    Status COLD or OVERHEATED schedule a new check
    """,
    {
        rulename: "on-temp-status-bad",
        subscribe_to: SUBJECT_PROPERTY_CHANGED,
        ruledata: {
            filters: [
                Filter(lambda payload: payload[PayloadConst.PROPERTY_NAME] == "temp_status" and
                                       (payload[PayloadConst.VALUE] == "COLD" or payload[PayloadConst.VALUE] == "OVERHEATED"))
            ],
            processing: [
                Route(event_type="temp-status-bad", payload=lambda self: {
                    "tempc": str(self.subject.get("tempc")),
                    "status": self.payload.get("value")
                }, dispatch_policy=DispatchPolicyConst.DIRECT),
                SetSubjectProperty("lastTempStatusChanged", lambda: datetime.now().isoformat(), muted=True),
                Schedule(
                    key="schedule_temp_status_uid",
                    event_type="temp-status-recheck",
                    payload=lambda payload: {
                        "old_value": payload["value"]
                    },
                    when=lambda: datetime.now(timezone.utc) + timedelta(seconds=30)
                ),
            ],
        },
    },

    """
    Recheck
    """,
    {
        rulename: "on-temp-status-recheck",
        subscribe_to: "temp-status-recheck",
        ruledata: {
            filters: [
                Filter(lambda self: self.payload.get("old_value") == self.subject.get("temp_status"))
            ],
            processing: [
                Route(event_type="temp-status-still-bad", payload=lambda self: {
                    "status": self.payload.get("old_value"),
                    "seconds": (datetime.now() - parse(self.subject.get("lastTempStatusChanged"))).seconds
                }, dispatch_policy=DispatchPolicyConst.DIRECT),
                Schedule(
                    key="schedule_temp_status_uid",
                    event_type="temp-status-recheck",
                    payload=lambda payload: {
                        "old_value": payload["old_value"]
                    },
                    when=lambda: datetime.now(timezone.utc) + timedelta(seconds=15)
                ),
            ],
        },
    },
]

