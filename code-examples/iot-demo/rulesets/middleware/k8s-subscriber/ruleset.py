
from krules_core.base_functions import *
from krules_core import RuleConst as Const

rulename = Const.RULENAME
subscribe_to = Const.SUBSCRIBE_TO
ruledata = Const.RULEDATA
filters = Const.FILTERS
processing = Const.PROCESSING

from krules_core.providers import proc_events_rx_factory, subject_factory
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
    check in the labels if the service represents a frontend application (device manager or dashboard) 
    and in the case set the url as a reactive property
    """,
    {
        rulename: "on-ksvc-update-set-url-for-apps",
        subscribe_to: [
            "dev.knative.apiserver.resource.add",
            "dev.knative.apiserver.resource.update",
        ],
        ruledata: {
            filters: [
                Filter(
                    lambda payload:
                        "address" in payload.get("status", {})
                ),
            ],
            processing: [
                Process(
                    lambda payload: (
                        # a specific subject is created to store reactive properties for frontend apps
                        payload.setdefault("_subject", subject_factory(
                            f"ksvc:{payload['metadata']['labels']['krules.airspot.dev/type']}:{payload['metadata']['name'].split('-dashboard')[0]}"
                        )),
                        # this allows us to be more selective in defining the trigger
                        payload["_subject"].set_ext("app", payload['metadata']['labels']['krules.airspot.dev/type']),
                        # we set the url as reactive property so that can react when the service became available
                        # we do not use the subject cache to prevent multiple events
                        # as during the creation phase we could have update events in quick succession
                        payload["_subject"].set("url", payload['status']['url'], use_cache=False)
                    )
                )
            ]
        }
    },
    """
    flush the subject when a frontend application is deleted
    """,
    {
        rulename: "on-ksvc-delete-flush-app-subject",
        subscribe_to: [
            "dev.knative.apiserver.resource.delete",
        ],
        ruledata: {
            processing: [
                Process(
                    lambda payload:
                        subject_factory(
                            f"ksvc:{payload['metadata']['labels']['krules.airspot.dev/type']}:{payload['metadata']['name']}"
                        ).flush()
                )
            ]
        }
    },

]

