
from krules_core.providers import proc_events_rx_factory
import pprint

from krules_core import RuleConst as Const
from krules_core.base_functions import *
from k8s_functions import *
from krules_env import publish_proc_events_all

rulename = Const.RULENAME
subscribe_to = Const.SUBSCRIBE_TO
ruledata = Const.RULEDATA
filters = Const.FILTERS
processing = Const.PROCESSING

LBL_INJECT = "krules.airspot.dev/injection"
LBL_INJECTED = "krules.airspot.dev/injected"

DEFAULT_BROKER = "default"
PROCEVENTS_BROKER = "procevents"
PROCEVENTS_TRIGGER = "procevents-trigger"
MANAGED_APISERVERSOURCE = "krules-injected"
NS_WATCHER_SERVICEACCOUNT = "krules-ns-watcher-serviceaccount"
NS_WATCHER_ROLE = "krules-ns-watcher-role"
NS_WATCHER_ROLEBINDING = "krules-ns-watcher-rolebinding"
SYSTEM_NS = "krules-system"

APISERVERSOURCE_APIVERSION = "sources.knative.dev/v1beta1"


proc_events_rx_factory().subscribe(
    on_next=pprint.pprint
)
proc_events_rx_factory().subscribe(
    on_next=publish_proc_events_all,
)


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


dispose_injection_rules = [
    """
    When a namespace is tagged for injection, an event of type "ensure-resources"
    is produced
    """,
    {
        rulename: "ns-dispose-ensure-resources",
        subscribe_to: ["k8s.resource.add", "k8s.resource.update"],
        ruledata: {
            filters: [
                PayloadMatchOne("$._event_info.kind", "Namespace"),
                Filter(
                    lambda payload: (
                            payload.get("object", {})
                            .get("metadata", {})
                            .get("labels", {})
                            .get(LBL_INJECT, "") == "enabled"
                    )
                )
            ],
            processing: [
                Route(
                    event_type="ensure-resources",
                    payload=lambda subject: {
                        "namespace": subject.get_ext("name")
                    }
                )
            ]
        }
    },
    """
    When a resource labeled as injected in a injected namespace is deleted
    an event of type "ensure-resources" is produced
    """,
    {
        rulename: "on-delete-dispose-ensure-resources",
        subscribe_to: ["k8s.resource.delete"],
        ruledata: {
            filters: [
                # check if source namespace injection is enabled
                K8sObjectsQuery(
                    apiversion="v1",
                    kind="Namespace",
                    selector={
                        "krules.airspot.dev/injection": "enabled",
                    },
                    returns=lambda subject: lambda objs: (
                        bool(objs.get_or_none(name=subject.get_ext("namespace")))
                    )
                )
            ],
            processing: [
                Route(
                    event_type="ensure-resources",
                    payload=lambda subject: {
                        "namespace": subject.get_ext("namespace")
                    }
                )
            ]
        }
    },
]

injection_rules = [
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
                Route("ensure-injected-resource", payload=lambda payload: {
                    "apiversion": "eventing.knative.dev/v1",
                    "kind": "Trigger",
                    "namespace": payload.get("namespace"),
                    "name": PROCEVENTS_TRIGGER,
                    "spec": {
                        "broker": DEFAULT_BROKER,
                        "filter": {
                            "attributes": {
                                "type": "rule-proc-event"
                            }
                        },
                        "subscriber": {
                            "ref": {
                                "apiVersion": "eventing.knative.dev/v1",
                                "kind": "Broker",
                                "name": PROCEVENTS_BROKER
                            }
                        }
                    }
                }),
                Route("ensure-injected-resource", payload=lambda payload: {
                    "apiversion": "v1",
                    "kind": "ServiceAccount",
                    "namespace": payload.get("namespace"),
                    "name": NS_WATCHER_SERVICEACCOUNT,
                }),
                Route("ensure-injected-resource", payload=lambda payload: {
                    "apiversion": "rbac.authorization.k8s.io/v1",
                    "kind": "Role",
                    "namespace": payload.get("namespace"),
                    "name": NS_WATCHER_ROLE,
                    "rules": [
                        {
                            "apiGroups": ["krules.airspot.dev"],
                            "resources": [
                                "configurationproviders",
                            ],
                            "verbs": [
                                "list",
                                "get",
                                "watch",
                            ]
                        },
                        {
                            "apiGroups": ["eventing.knative.dev", "serving.knative.dev"],
                            "resources": [
                                "brokers",
                                "triggers",
                                "services"
                            ],
                            "verbs": [
                                "list",
                                "get",
                                "watch",
                            ]
                        },
                    ]
                }),
                Route("ensure-injected-resource", payload=lambda payload: {
                    "apiversion": "rbac.authorization.k8s.io/v1",
                    "kind": "RoleBinding",
                    "namespace": payload.get("namespace"),
                    "name": NS_WATCHER_ROLEBINDING,
                    "subjects": [
                        {
                            "kind": "ServiceAccount",
                            "name": NS_WATCHER_SERVICEACCOUNT,
                        }
                    ],
                    "roleRef": {
                        "kind": "Role",
                        "name": NS_WATCHER_ROLE,
                        "apiGroup": "rbac.authorization.k8s.io"
                    }
                }),
                Route("ensure-injected-resource", payload=lambda payload: {
                    "apiversion": APISERVERSOURCE_APIVERSION,
                    "kind": "ApiServerSource",
                    "namespace": payload.get("namespace"),
                    "name": MANAGED_APISERVERSOURCE,
                    "spec": {
                        "serviceAccountName": NS_WATCHER_SERVICEACCOUNT,
                        "mode": "Resource",
                        "resources": [
                            {
                                "apiVersion": "krules.airspot.dev/v1alpha1",
                                "kind": "ConfigurationProvider"
                            },
                            {
                                "apiVersion": "eventing.knative.dev/v1",
                                "kind": "Broker",
                                "selector": {
                                    "matchLabels": {
                                        "krules.airspot.dev/injected": "injected"
                                    }
                                }
                            },
                            {
                                "apiVersion": "eventing.knative.dev/v1",
                                "kind": "Trigger",
                                "selector": {
                                    "matchLabels": {
                                        "krules.airspot.dev/injected": "injected"
                                    }
                                }
                            },
                            {
                                "apiVersion": "serving.knative.dev/v1",
                                "kind": "Service",
                            },

                        ],
                        "sink": {
                            "ref": {
                                "apiVersion": "v1",
                                "kind": "Service",
                                "name": "apiserversource-subscriber",
                                "namespace": SYSTEM_NS
                            }
                        }
                    },
                })
            ]
        },
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

cleanup_rules = [
    {
        rulename: "ns-delete-all",
        subscribe_to: ["k8s.resource.add", "k8s.resource.update"],
        ruledata: {
            filters: [
                # check ns label
                Filter(
                    lambda payload: (
                            payload.get("object", {})
                            .get("metadata", {})
                            .get("labels", {})
                            .get(LBL_INJECT, "") == "disabled"
                    )
                )
            ],
            processing: [
                K8sObjectsQuery(
                    apiversion="rbac.authorization.k8s.io/v1", kind="RoleBinding",
                    namespace=lambda subject: subject.get_ext("name"),
                    selector={
                        "krules.airspot.dev/injected": "injected"
                    },
                    foreach=lambda obj: (
                        obj.delete()
                    )
                ),
                K8sObjectsQuery(
                    apiversion="rbac.authorization.k8s.io/v1", kind="Role",
                    namespace=lambda subject: subject.get_ext("name"),
                    selector={
                        "krules.airspot.dev/injected": "injected"
                    },
                    foreach=lambda obj: (
                        obj.delete()
                    )
                ),
                K8sObjectsQuery(
                    apiversion="v1", kind="ServiceAccount",
                    namespace=lambda subject: subject.get_ext("name"),
                    selector={
                        "krules.airspot.dev/injected": "injected"
                    },
                    foreach=lambda obj: (
                        obj.delete()
                    )
                ),
                K8sObjectsQuery(
                    apiversion=APISERVERSOURCE_APIVERSION, kind="ApiServerSource",
                    namespace=lambda subject: subject.get_ext("name"),
                    selector={
                        "krules.airspot.dev/injected": "injected"
                    },
                    foreach=lambda obj: (
                        obj.delete()
                    )
                ),
                K8sObjectsQuery(
                    apiversion="eventing.knative.dev/v1", kind="Trigger",
                    namespace=lambda subject: subject.get_ext("name"),
                    selector={
                        "krules.airspot.dev/injected": "injected"
                    },
                    foreach=lambda obj: (
                        obj.delete()
                    )
                ),
                K8sObjectsQuery(
                    apiversion="eventing.knative.dev/v1", kind="Broker",
                    namespace=lambda subject: subject.get_ext("name"),
                    selector={
                        "krules.airspot.dev/injected": "injected"
                    },
                    foreach=lambda obj: (
                        obj.delete()
                    )
                ),
            ]
        },
    },
]

rulesdata = dispose_injection_rules + injection_rules + cleanup_rules
