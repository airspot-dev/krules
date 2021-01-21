from krules_core.base_functions import *

from krules_core import RuleConst as Const

rulename = Const.RULENAME
subscribe_to = Const.SUBSCRIBE_TO
ruledata = Const.RULEDATA
filters = Const.FILTERS
processing = Const.PROCESSING

from app_functions.k8s import K8sObjectCreate, K8sObjectsQuery, K8sObjectUpdate, K8sObjectDelete, k8s_subject
from krules_core.providers import proc_events_rx_factory
from krules_env import publish_proc_events_errors, publish_proc_events_all, publish_proc_events_filtered
import hashlib
from django.apps import apps
from django.conf import settings
from django.db.utils import InterfaceError
apps.populate(settings.INSTALLED_APPS)
from configs.models import Configuration


proc_events_rx_factory().subscribe(
    on_next=publish_proc_events_all,
)


# proc_events_rx_factory().subscribe(
#     on_next=publish_proc_events_errors,
# )

def update_route_traffic(route):
    new_traffic = []
    new_traffic_percent = 0

    for config_traffic in Configuration.objects.filter(service__name=route["metadata"]["name"]):
        new_traffic_percent += config_traffic.traffic
        new_traffic.append({
            "configurationName": config_traffic.name,
            "percent": config_traffic.traffic
        })
    if new_traffic_percent == 100:
        route["spec"]["traffic"] = new_traffic


class SetHashedResourceName(RuleFunctionBase):

    def execute(self, name, data, payload_dest):
        hash_str = hashlib.md5(json.dumps(data, sort_keys=True).encode()).hexdigest()
        self.payload[payload_dest] = "%s-%s" % (name, hash_str)


rulesdata = [

    """
    On Service model creation create the first Configuration and Route
    """,
    {
        rulename: "on-model-creation-create-config",
        subscribe_to: "django.orm.post_save",
        ruledata: {
            filters: [
                Returns(
                    lambda _: (
                            _.subject.event_info().get("djangomodel") == "service" and
                            _.payload["signal_kwargs"]["created"]
                    )
                )
            ],
            processing: [
                SetHashedResourceName(
                    name=lambda _: _.payload["data"]["name"],
                    data=lambda _: {
                        "image": _.payload["data"]["image"],
                        "T_VERSION": _.payload["data"]["t_version"],
                    },
                    payload_dest="configuration_name"
                ),
                K8sObjectCreate(
                    lambda _: {
                        "apiVersion": "serving.knative.dev/v1",
                        "kind": "Configuration",
                        "metadata": {
                            "name": _.payload["configuration_name"],
                            "labels": {
                                "django.orm.configs/service": _.payload["data"]["id"],
                            }
                        },
                        "spec": {
                            "template": {
                                "metadata": {
                                    "labels": {
                                        "django.orm.configs/service": _.payload["data"]["id"],
                                        "knative.dev/type": "container",
                                    }
                                },
                                "spec": {
                                    "containers": [
                                        {
                                            "image": _.payload["data"]["image"],
                                            "imagePullPolicy": "Always",
                                            "env": [
                                                {
                                                    "name": "T_VERSION",
                                                    "value": _.payload["data"]["t_version"],
                                                }
                                            ]
                                        }
                                    ]
                                }
                            }
                        }

                    }
                ),
                K8sObjectCreate(
                    lambda _: {
                        "apiVersion": "serving.knative.dev/v1",
                        "kind": "Route",
                        "metadata": {
                            "name": _.payload["data"]["name"],
                            "labels": {
                                "django.orm.configs/service": _.payload["data"]["id"],
                            }
                        },
                        "spec": {
                            "traffic": [
                                {
                                    "configurationName": _.payload["configuration_name"],
                                    "percent": 100,
                                }
                            ]
                        }
                    }
                ),
            ],
        },
    },
    """
    On Service model update create a new Configuration and update Route
    """,
    {
        rulename: "on-model-saving-update-route",
        subscribe_to: "django.orm.post_save",
        ruledata: {
            filters: [
                Returns(
                    lambda _: (
                            _.subject.event_info().get("djangomodel") == "service"
                            and not _.payload["signal_kwargs"]["created"]
                    )
                )
            ],
            processing: [
                SetHashedResourceName(
                    name=lambda _: _.payload["data"]["name"],
                    data=lambda _: {
                        "image": _.payload["data"]["image"],
                        "T_VERSION": _.payload["data"]["t_version"],
                    },
                    payload_dest="configuration_name"
                ),
                K8sObjectCreate(
                    lambda _: {
                        "apiVersion": "serving.knative.dev/v1",
                        "kind": "Configuration",
                        "metadata": {
                            "name": _.payload["configuration_name"],
                            "labels": {
                                "django.orm.configs/service": _.payload["data"]["id"],
                            }
                        },
                        "spec": {
                            "template": {
                                "metadata": {
                                    "labels": {
                                        "django.orm.configs/service": _.payload["data"]["id"],
                                        "knative.dev/type": "container",
                                    }
                                },
                                "spec": {
                                    "containers": [
                                        {
                                            "image": _.payload["data"]["image"],
                                            "imagePullPolicy": "Always",
                                            "env": [
                                                {
                                                    "name": "T_VERSION",
                                                    "value": _.payload["data"]["t_version"],
                                                }
                                            ]
                                        }
                                    ]
                                }
                            }
                        }

                    }
                ),
                K8sObjectUpdate(
                    apiversion="serving.knative.dev/v1",
                    kind="Route",
                    name=lambda _: _.payload["data"]["name"],
                    func=lambda _: lambda obj: (
                        obj.update(
                            {
                                "spec": {
                                    "traffic": [
                                        {
                                            "configurationName": _.payload["configuration_name"],
                                            "percent": 100,
                                        }
                                    ]
                                }
                            }
                        )
                    ),
                ),
            ],
        },
    },
    """
    On Configuration model update set routes 
    """,
    {
        rulename: "on-configuration-saving-update-traffic",
        subscribe_to: "django.orm.post_save",
        ruledata: {
            filters: [
                Returns(
                    lambda _: (
                            _.subject.event_info().get("djangomodel") == "configuration"
                            and not _.payload["signal_kwargs"]["created"]
                    )
                )
            ],
            processing: [
                K8sObjectUpdate(
                    apiversion="serving.knative.dev/v1",
                    kind="Route",
                    name=lambda _: _.payload["data"]["service"],
                    func=lambda obj: (
                        update_route_traffic(obj)
                    ),
                ),
            ],
        },
    },
    """
    On Configuration model delete 
    """,
    {
        rulename: "on-configuration-delete",
        subscribe_to: "django.orm.post_delete",
        ruledata: {
            filters: [
                Returns(
                    lambda _: (
                            _.subject.event_info().get("djangomodel") == "configuration"
                    )
                )
            ],
            processing: [
                K8sObjectDelete(
                    apiversion="serving.knative.dev/v1",
                    kind="Configuration",
                    name=lambda _: _.payload["data"]["name"]
                ),
            ],
        },
    },
    """
    On Service model delete route
    """,
    {
        rulename: "on-service-delete",
        subscribe_to: "django.orm.post_delete",
        ruledata: {
            filters: [
                Returns(
                    lambda _: (
                            _.subject.event_info().get("djangomodel") == "service"
                    )
                )
            ],
            processing: [
                K8sObjectDelete(
                    apiversion="serving.knative.dev/v1",
                    kind="Route",
                    name=lambda _: _.payload["data"]["name"]
                ),
            ],
        },
    },

]

