from krules_core.base_functions import *
from krules_core import RuleConst as Const

rulename = Const.RULENAME
subscribe_to = Const.SUBSCRIBE_TO
ruledata = Const.RULEDATA
filters = Const.FILTERS
processing = Const.PROCESSING
from krules_core.providers import proc_events_rx_factory
from krules_env import publish_proc_events_errors, publish_proc_events_all, publish_proc_events_filtered

# proc_events_rx_factory().subscribe(
#   on_next=publish_proc_events_all,
# )
proc_events_rx_factory().subscribe(
 on_next=publish_proc_events_errors,
)

rulesdata = [
    """
    Switch subject (prepending k8s:)
    type changes in k8s.resources.update
    """,
    {
        rulename: "on-resource-event-switch-subject",
        subscribe_to: [
            "dev.knative.apiserver.resource.add",
            "dev.knative.apiserver.resource.update",
            "dev.knative.apiserver.resource.delete",
        ],
        ruledata: {
            processing: [
                Route(
                    lambda ctx:   # type
                        "k8s.resource.{}".format(ctx.type.split(".")[-1]),
                    lambda ctx:   # subject
                        "k8s:{}".format(ctx.subject.name), dispatch_policy=DispatchPolicyConst.DIRECT
                )
            ]
        }
    },
]
