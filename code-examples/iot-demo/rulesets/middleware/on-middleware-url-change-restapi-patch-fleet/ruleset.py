import requests
from app_functions.restapiclient import DoPatchApiCall
from krules_core.base_functions import *
from krules_core import RuleConst as Const
from krules_core.event_types import SUBJECT_PROPERTY_CHANGED

from krules_core.providers import proc_events_rx_factory
from krules_env import publish_proc_events_errors, publish_proc_events_all  #, publish_proc_events_filtered

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
    Post url value to appropriate fleet model field
    """,
    {
        rulename: "on-url-changed-postapi",
        subscribe_to: [SUBJECT_PROPERTY_CHANGED],
        ruledata: {
            filters: [
                SubjectNameMatch("ksvc:(?P<app>.+):(?P<fleet>.+)"),
            ],
            processing: [
                DoPatchApiCall(
                    path=lambda payload: f"/device_manager/fleet/{payload['subject_match']['fleet']}/",
                    json=lambda payload: {
                             payload["subject_match"]["app"]: payload["value"],
                         },
                )
            ]
        }
    },
]


