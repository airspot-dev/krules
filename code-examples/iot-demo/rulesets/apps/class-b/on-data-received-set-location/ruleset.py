
from krules_core.base_functions import *
from krules_core import RuleConst as Const

from krules_core.providers import proc_events_rx_factory
from krules_env import publish_proc_events_errors, publish_proc_events_all  #, publish_proc_events_filtered

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
 on_next=publish_proc_events_errors,
)

rulesdata = [
    """
    Always store coords in subject, Initialize starting point too if needed
    """,
    {
        rulename: "manage-device-status-store-coords",
        subscribe_to: "data-received",
        ruledata: {
            processing: [
                SetLocationProperties()
            ],
        },
    },
]

