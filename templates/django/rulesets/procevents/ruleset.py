from datetime import datetime, timezone

from krules_core import RuleConst as Const
from krules_core.base_functions import *
from krules_env import RULE_PROC_EVENT

from krules_djangoapps_procevents.models import ProcessingEvent


rulename = Const.RULENAME
subscribe_to = Const.SUBSCRIBE_TO
ruledata = Const.RULEDATA
filters = Const.FILTERS
processing = Const.PROCESSING


rulesdata = [
    """
    On tick route scheduled events
    """,
    {
        rulename: "store-procevents-on-django",
        subscribe_to: RULE_PROC_EVENT,
        ruledata: {
            processing: [
                Process(lambda payload:
                        ProcessingEvent.objects.create(
                            rule_name=payload["name"],
                            type=payload["type"],
                            subject=payload["subject"],
                            event_info=payload["event_info"],
                            payload=payload["payload"],
                            time=payload["event_info"].get("time", datetime.now(timezone.utc).isoformat()),
                            filters=payload["filters"],
                            processing=payload["processing"],
                            got_errors=payload["got_errors"],
                            passed=payload["passed"],
                            source=payload.get("source", "-"),
                            origin_id=payload["event_info"].get("originid", "-")
                        )
                )
            ]
        }
    },
]