from datetime import datetime, timezone, timedelta
from krules_core import event_types
from krules_core.base_functions import *
from krules_core import RuleConst as Const

from krules_core.providers import proc_events_rx_factory
from krules_env import publish_proc_events_all  #, publish_proc_events_filtered
import os
import jsonpath_rw_ext as jp

from app_functions import Schedule

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
    Create the original event when a location change is received.
    The same event can be received from outside because it will be rescheduled in case it fails calling API service
    """,
    {
        rulename: "on-location-changed-notify-postextapi",
        subscribe_to: event_types.SUBJECT_PROPERTY_CHANGED,
        ruledata: {
            filters: [
                OnSubjectPropertyChanged("location"),
            ],
            processing: [
                Route("do-extapi-post", payload=lambda self: {
                    "location": self.payload["value"],
                    "coords": self.subject.get("coords"),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }, dispatch_policy=DispatchPolicyConst.NEVER)
            ],
        },
    },
    """
    Actually make call to API service
    """,
    {
        rulename: "on-do-extapi-post",
        subscribe_to: "do-extapi-post",
        ruledata: {
            processing: [
                PostExtApi(
                    location=lambda payload: payload["location"],
                    coords=lambda payload: payload["coords"],
                    timestamp=lambda payload: payload["timestamp"],
                )
            ]
        }
    },
    """
    Manage exception
    """,
    {
        rulename: "on-do-extapi-post-errors",
        subscribe_to: "{}-errors".format(os.environ["K_SERVICE"]),
        ruledata: {
            filters: [
                Filter(lambda payload:
                       payload.get("name") == "on-do-extapi-post" and
                       jp.match1("$.processing[*].exception", payload) == "requests.exceptions.HTTPError" and
                       jp.match1("$.processing[*].exc_extra_info.response_code", payload) == 503)
            ],
            processing: [
                Schedule(
                    event_type="do-extapi-post",
                    payload=lambda payload: payload["payload"],
                    when=lambda: datetime.now(timezone.utc) + timedelta(seconds=10)
                ),
            ]
        }
    }
]

