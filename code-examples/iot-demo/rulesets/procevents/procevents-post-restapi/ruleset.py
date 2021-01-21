
from krules_core.base_functions import *
from krules_core import RuleConst as Const
import requests
from datetime import datetime

from krules_core.providers import configs_factory

rulename = Const.RULENAME
subscribe_to = Const.SUBSCRIBE_TO
ruledata = Const.RULEDATA
filters = Const.FILTERS
processing = Const.PROCESSING

from krules_env import RULE_PROC_EVENT
from app_functions.restapiclient import DoPostApiCall

rulesdata = [
    """
    Post processed events to API
    """,
    {
        rulename: "post-full-procevents-data",
        subscribe_to: RULE_PROC_EVENT,
        ruledata: {
            processing: [
                DoPostApiCall(
                    path="/procevent/",
                    json=lambda self: {
                        "rule_name": self.payload["name"],
                        "type": self.payload["type"],
                        "subject": self.payload["subject"],
                        "event_info": self.payload["event_info"],
                        "payload": self.payload["payload"],
                        "time": self.payload["event_info"].get("time", datetime.now().isoformat()),
                        "filters": self.payload["filters"],
                        "processing": self.payload["processing"],
                        "got_errors": self.payload["got_errors"],
                        "processed": self.payload["processed"],
                        "origin_id": self.payload["event_info"].get("originid", "-")
                    }
                ),
            ],
        },
    },
]

