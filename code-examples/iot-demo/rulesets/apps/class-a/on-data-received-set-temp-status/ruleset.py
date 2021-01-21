
from krules_core.base_functions import *
from krules_core import RuleConst as Const

from krules_core.providers import proc_events_rx_factory
from krules_env import publish_proc_events_errors, publish_proc_events_all  #, publish_proc_events_filtered
from krules_core.event_types import SUBJECT_PROPERTY_CHANGED
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
    Store temp property
    """,
    {
        rulename: "manage-device-status-store-temp",
        subscribe_to: "data-received",
        ruledata: {
            filters: [
                Filter(lambda payload: "tempc" in payload["data"])
            ],
            processing: [
                SetSubjectProperty("tempc", lambda payload: payload["data"]["tempc"], use_cache=False)
            ],
        },
    },

    """
    Set temp_status COLD 
    """,
    {
        rulename: "on-tempc-changed-check-cold",
        subscribe_to: SUBJECT_PROPERTY_CHANGED,
        ruledata: {
            filters: [
                OnSubjectPropertyChanged("tempc"),
                Filter(lambda self:
                       float(self.payload.get("value")) < float(self.subject.get("temp_min"))
                       ),
            ],
            processing: [
                SetSubjectProperty("temp_status", "COLD"),
            ],
        }
    },

    """
    Set temp_status NORMAL 
    """,
    {
        rulename: "on-tempc-changed-check-normal",
        subscribe_to: SUBJECT_PROPERTY_CHANGED,
        ruledata: {
            filters: [
                OnSubjectPropertyChanged("tempc"),
                Filter(lambda self:
                       float(self.subject.get("temp_min")) <= float(self.payload.get("value")) < float(self.subject.get("temp_max"))
                       ),
            ],
            processing: [
                SetSubjectProperty("temp_status", "NORMAL"),
            ],
        }
    },

    """
    Set temp_status OVERHEATED 
    """,
    {
        rulename: "on-tempc-changed-check-overheated",
        subscribe_to: SUBJECT_PROPERTY_CHANGED,
        ruledata: {
            filters: [
                OnSubjectPropertyChanged("tempc"),
                Filter(lambda self:
                       float(self.payload.get("value")) >= float(self.subject.get("temp_max"))
                       )
            ],
            processing: [
                SetSubjectProperty("temp_status", "OVERHEATED"),
            ],
        }
    },

    """
    Since we have already intercepted the prop changed event inside the container we need to send it out 
    explicitily (both tempc and temp_status)
    """,
    {
        rulename: "temp-status-propagate",
        subscribe_to: SUBJECT_PROPERTY_CHANGED,
        ruledata: {
            filters: [
                OnSubjectPropertyChanged(lambda x: x in ("temp_status", "tempc")),
            ],
            processing: [
                Route(dispatch_policy=DispatchPolicyConst.DIRECT)
            ]
        },
    },
]

