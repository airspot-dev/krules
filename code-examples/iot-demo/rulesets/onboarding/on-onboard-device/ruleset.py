
from krules_core.base_functions import *
from krules_core import RuleConst as Const
import requests
import uuid

rulename = Const.RULENAME
subscribe_to = Const.SUBSCRIBE_TO
ruledata = Const.RULEDATA
filters = Const.FILTERS
processing = Const.PROCESSING

from krules_core.providers import proc_events_rx_factory
from krules_env import publish_proc_events_errors, publish_proc_events_all  #, publish_proc_events_filtered

# try:
#     from ruleset_functions import *
# except ImportError:
#     # for local development
#     from .ruleset_functions import *
    
proc_events_rx_factory().subscribe(
  on_next=publish_proc_events_all,
)
# proc_events_rx_factory().subscribe(
#  on_next=publish_proc_events_errors,
# )

rulesdata = [
    """
    Set the basic properties of the device and the initial status as 'READY'
    The status will become 'ACTIVE' upon receipt of the first message
    """,
    {
        rulename: "on-onboard-device-store-properties",
        subscribe_to: ["onboard-device"],
        ruledata: {
            filters: [
                Filter(lambda payload: "data" in payload and "class" in payload),
            ],
            processing: [
                FlushSubject(),
                SetSubjectProperties(lambda payload: payload["data"]),
                SetSubjectExtendedProperty("deviceclass", lambda payload: payload["class"]),
                SetSubjectExtendedProperty("fleet", lambda payload: payload["fleet"], use_cache=False),
                SetSubjectExtendedProperty("subjecttype", "device"),
                SetSubjectExtendedProperty("phase", "onboarded"),
                SetSubjectProperty('schedule_status_uid', lambda: str(uuid.uuid4()), muted=True),
                StoreSubject(),  # properties are immediateley available before reacting to status change
                SetSubjectProperty('status', 'READY'),
            ]
        }
    },
]
