
from k8s_functions import k8s_subject
from krules_core.base_functions.processing import Route, DispatchPolicyConst, Process

from krules_core import RuleConst as Const
from krules_core.providers import proc_events_rx_factory
from krules_env import publish_proc_events_all

rulename = Const.RULENAME
subscribe_to = Const.SUBSCRIBE_TO
ruledata = Const.RULEDATA
filters = Const.FILTERS
processing = Const.PROCESSING




# proc_events_rx_factory().subscribe(
#     on_next=publish_proc_events_all,
# )
# import pprint
# proc_events_rx_factory().subscribe(
#     on_next=pprint.pprint
# )


class _RouteToLabeledK8sSubject(Route):

    def execute(self, **kwargs):

        event_type = "k8s.resource.{}".format(self.event_type.split(".")[-1])
        # the apiserversource uses the api resource path as the subject
        # with an issue for namespace resources
        subject = k8s_subject(self.payload,
                              resource_path=self.payload.get("kind") == "Namespace" and "/api/v1/namespaces/{}".format(
                                    self.payload.get("metadata").get("name")
                              ) or str(self.subject))
        if event_type != "k8s.resource.delete":
            # injected resources
            if self.payload.get("metadata", {}).get("labels", {}).get("krules.airspot.dev/injected") == "injected":
                subject.set_ext("krulesinjected", "injected", use_cache=False)
            # configuration provider generated cm
            if self.payload.get("kind") == "ConfigMap" and \
                    self.payload.get("metadata", {}).get("labels", {}).get("config.krules.airspot.dev/provider", False):
                subject.set_ext("krulesconfig", "provided", use_cache=False)
        payload = {
            'object': self.payload
        }
        payload["_event_info"] = payload["object"].pop("_event_info")

        super().execute(event_type, subject, payload, dispatch_policy=DispatchPolicyConst.DIRECT)


rulesdata = [

    """
    allows to process the event using the krules subject implementation (adds extended attributes)
    """,
    {
        rulename: "on-resource-event-fwd",
        subscribe_to: [
            "dev.knative.apiserver.resource.add",
            "dev.knative.apiserver.resource.update",
            "dev.knative.apiserver.resource.delete",
        ],
        ruledata: {
            processing: [
                _RouteToLabeledK8sSubject(),
            ]
        }

    },
]