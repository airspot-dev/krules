
from krules_core import RuleConst as Const

from krules_core.base_functions import *
from k8s_functions import *

rulename = Const.RULENAME
subscribe_to = Const.SUBSCRIBE_TO
ruledata = Const.RULEDATA
filters = Const.FILTERS
processing = Const.PROCESSING

DEFAULT_BROKER = "default"
PROCEVENTS_BROKER = "procevents"
LBL_INJECTED = "krules.dev/injected"


class K8sQueryResourceDoesNotExists(K8sObjectsQuery):

    def execute(self, **kwargs):

        apiversion = self.payload.get("apiversion")
        kind = self.payload.get("kind")
        namespace = self.payload.get("namespace")

        return super().execute(
            apiversion=apiversion, kind=kind,
            namespace=namespace,
            returns=lambda objs: objs.get_or_none(name=self.payload.get("name")) is None
        )

class K8sCreateInjectedResource(K8sObjectCreate):

    def execute(self, **kwargs):

        resource = {
            "apiVersion": self.payload.pop("apiversion"),
            "kind": self.payload.pop("kind"),
            "metadata": {
                "name": self.payload.pop("name"),
                "namespace": self.payload.pop("namespace"),
                "labels": {
                    LBL_INJECTED: "injected"
                }
            }
        }

        resource.update({k: v for k, v in self.payload.items() if not k.startswith('_')})

        super().execute(resource)


rulesdata = [
    """
    Ensure brokers live in ns
    """,
    {
        rulename: "on-ns-validated-ensure-resources",
        subscribe_to: [
            "validate-namespace-create",
            "validate-namespace-update",
        ],
        ruledata: {
            processing: [
                Route(
                    event_type="ensure-resources",
                    payload=lambda payload: {
                        "namespace": payload["request"]["namespace"]
                    }
                )
            ]
        }
    },
    """
    When a resource labeled as injected  is deleted ensure resources again
    """,
    {
        rulename: "on-delete-dispose-ensure-resources",
        subscribe_to: [
            "validate-broker-delete"
        ],
        ruledata: {
            filters: [
                PayloadMatchOne(
                    "$.request.oldObject.metadata.labels",
                    lambda labels: LBL_INJECTED in labels and labels[LBL_INJECTED] == "injected"
                )
            ],
            processing: [
                Route(
                    event_type="ensure-resources",
                    payload=lambda payload: {
                        "namespace": payload["request"]["namespace"]
                    }
                )
            ]
        }
    },
    """
    Dispose objects creation
    """,
    {
        rulename: "do-ensure-resources",
        subscribe_to: "ensure-resources",
        ruledata: {
            processing: [
                Route("ensure-injected-resource", payload=lambda payload: {
                    "apiversion": "eventing.knative.dev/v1",
                    "kind": "Broker",
                    "namespace": payload.get("namespace"),
                    "name": DEFAULT_BROKER,
                }),
                Route("ensure-injected-resource", payload=lambda payload: {
                    "apiversion": "eventing.knative.dev/v1",
                    "kind": "Broker",
                    "namespace": payload.get("namespace"),
                    "name": PROCEVENTS_BROKER,
                }),
           ]
        }
    },
    {
        rulename: "do-ensure-injected-resource",
        subscribe_to: "ensure-injected-resource",
        ruledata: {
            filters: [
                K8sQueryResourceDoesNotExists(),
            ],
            processing: [
                K8sCreateInjectedResource()
            ]
        }
    },

]