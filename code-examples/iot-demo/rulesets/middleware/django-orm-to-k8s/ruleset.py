import base64

from krules_core.base_functions import *
from krules_core import RuleConst as Const

from krules_core.providers import proc_events_rx_factory
from krules_env import publish_proc_events_errors, publish_proc_events_all  # , publish_proc_events_filtered

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
from app_functions import hashed
from k8s_functions import K8sObjectCreate, K8sObjectsQuery, K8sObjectDelete

try:
    from ruleset_functions import *
except ImportError:
    # for local development
    from .ruleset_functions import *

ENDPOINT_IMAGE = 'lorenzocampo/device-endpoint@sha256:97f7aebd823771ebd47f5b3ea9cd4f4d2f43666fddfe0810d9fa00e68dbcbdc0'
WS_APP_IMAGE = "lorenzocampo/dashboard-iot-demo@sha256:2d718c3e9c7ab38006d1d68e1eebe82299bc2e18545f7c904766c535e67bfbd0"

endpoint_rulesdata = [
    """
    On new fleet create, create endpoint 
    """,
    {
        rulename: "on-new-fleet-create-endpoint-service",
        subscribe_to: ["django.orm.post_save"],
        ruledata: {
            filters: [
                Filter(
                    lambda payload:
                    payload.get("signal_kwargs", {}).get("created", False)
                )
            ],
            processing: [
                SetEndpointHashedName("hashed_name"),
                SetClusterLocalLabel("lbl_cluster_local"),
                Route("ensure-apikey-secret"),
                # fetch broker address
                K8sObjectsQuery(
                    apiversion="eventing.knative.dev/v1",
                    kind="Broker",
                    returns=lambda payload: lambda objs: (
                        payload.setdefault("k_sink", objs.get(name="data-received").obj["status"]["address"]["url"])
                    )
                ),
                # TODO: use ConfigurationProvider
                K8sObjectsQuery(  # krules env specific conf
                    apiversion="v1",
                    kind="ConfigMap",
                    selector={
                        "config.krules.airspot.dev/provider": "config-krules-subjects-redis"
                    },
                    foreach=lambda payload: lambda obj:
                        payload.setdefault("cm-config-krules-subjects-redis", obj.name)
                ),
                K8sObjectCreate(
                    lambda payload: kservice(
                        labels={
                            **{
                                "krules.airspot.dev/type": "endpoint",
                            }, **payload.get("lbl_cluster_local")},
                        name=payload["data"]["name"],
                        revision_name=payload["hashed_name"],
                        containers=[{
                            "image": ENDPOINT_IMAGE,
                            "env": [
                                {
                                    "name": "K_SINK",
                                    "value": payload["k_sink"],
                                },
                                {
                                    "name": "API_KEY",
                                    "valueFrom": {
                                        "secretKeyRef": {
                                            "name": payload["hashed_name"],
                                            "key": "api_key"
                                        }
                                    }
                                }
                            ],
                            "envFrom": [
                                {
                                    "secretRef": {
                                        "name": "redis-credentials"
                                    }
                                },
                            ],
                            "volumeMounts": [
                                {
                                    "mountPath": "/krules/config/subjects-backends/redis",
                                    "name": "config-krules-subjects-redis",
                                    "readOnly": True
                                }
                            ]

                        }],
                        volumes=[{
                            "configMap": {
                                "name": payload["cm-config-krules-subjects-redis"]
                            },
                            "name": "config-krules-subjects-redis"
                        }],
                    )
                ),
            ]
        }
    },
    """
    On fleet update (manage api_key and cluster-local), update endpoint
    """,
    {
        rulename: "on-update-fleet-update-endpoint-service",
        subscribe_to: ["django.orm.post_save"],
        ruledata: {
            filters: [
                Filter(
                    lambda payload:
                    not payload.get("signal_kwargs", {}).get("created", False)
                )
            ],
            processing: [
                SetEndpointHashedName("hashed_name"),
                SetClusterLocalLabel("lbl_cluster_local"),
                Route("ensure-apikey-secret"),
                UpdateEndpointService(
                    secret_name=lambda payload: payload.get("hashed_name"),
                    lbl_cluster_local=lambda payload: payload.get("lbl_cluster_local")
                )
            ],
        }
    },
    """
    On fleet delete, delete endpoint
    """,
    {
        rulename: "on-fleet-delete-delete-endpoint-service",
        subscribe_to: "django.orm.post_delete",
        ruledata: {
            processing: [
                # delete endpoint
                K8sObjectDelete(
                    apiversion="serving.knative.dev/v1", kind="Service",
                    name=lambda payload: payload["data"]["name"]
                ),
                # delete apikey secret
                CleanUpSecrets(
                    other_than="-"
                )
            ]
        }
    }
]

secret_rulesdata = [
    """
    Responds to "ensure-secret", If secret already exists do nothing
    Create it otherwise
    Remove all others
    """,
    {
        rulename: "ensure-ingestion-apikey-secret",
        subscribe_to: "ensure-apikey-secret",
        ruledata: {
            filters: [
                K8sObjectsQuery(
                    apiversion="v1",
                    kind="Secret",
                    returns=lambda payload: lambda qobjs: (
                            qobjs.get_or_none(name=payload.get("hashed_name")) is None
                    )
                )
            ],
            processing: [
                K8sObjectCreate(lambda payload: {
                    "apiVersion": "v1",
                    "kind": "Secret",
                    "type": "Opaque",
                    "metadata": {
                        "name": payload["hashed_name"],
                        "labels": {
                            "app.krules.airspot.dev/owned-by": payload["data"]["name"]
                        }
                    },
                    "data": {
                        "api_key": base64.b64encode(payload["data"]["api_key"].encode("utf-8")).decode("utf-8")
                    }
                }),
                CleanUpSecrets(
                    owned_by=lambda payload: payload["data"]["name"],
                    other_than=lambda payload: payload["hashed_name"],
                ),
            ]
        }
    }
]

ws_app_rulesdata = [
    """
    On fleet create, create dashboard
    """,
    {
        rulename: "on-new-fleet-create-dashboard-service",
        subscribe_to: ["django.orm.post_save"],
        ruledata: {
            filters: [
                Filter(
                    lambda payload:
                    payload.get("signal_kwargs", {}).get("created", False)
                )
            ],
            processing: [
                SetClusterLocalLabel("lbl_cluster_local"),
                K8sObjectCreate(
                    lambda payload: kservice(
                        labels={**{
                            "krules.airspot.dev/type": "dashboard",
                        }, **payload.get("lbl_cluster_local")},
                        name="{}-dashboard".format(payload["data"]["name"]),
                        revision_name="{}-dashboard".format(payload["data"]["name"]),
                        containers=[{
                            "name": "web-app",
                            "image": WS_APP_IMAGE,
                            "envFrom": [{
                                "secretRef": {
                                    "name": "pusher-credentials",
                                },
                            }],
                            "env": [
                                {
                                    "name": "FLEET_CHANNEL",
                                    "value": payload["data"]["name"]
                                },
                                {
                                    "name": "FLEET_NAME",
                                    "value": payload["data"]["name"]
                                },
                                {
                                    "name": "DEVICE_DATA_EVENT",
                                    "value": "device-data"
                                },
                            ]
                        }]
                    )
                ),
            ]

        }
    },
    """
    On fleet update (manage cluster-local), update dashboard
    """,
    {
        rulename: "on-update-fleet-update-dashboard-service",
        subscribe_to: ["django.orm.post_save"],
        ruledata: {
            filters: [
                Filter(
                    lambda payload:
                    not payload.get("signal_kwargs", {}).get("created", False)
                )
            ],
            processing: [
                SetClusterLocalLabel("lbl_cluster_local"),
                UpdateDashboardService(
                    lbl_cluster_local=lambda payload: payload.get("lbl_cluster_local")
                )
            ]
        }
    },
    """
    On fleet delete, delete dashboard
    """,
    {
        rulename: "on-fleet-delete-delete-dashboard-service",
        subscribe_to: "django.orm.post_delete",
        ruledata: {
            processing: [
                # delete endpoint
                K8sObjectDelete(
                    apiversion="serving.knative.dev/v1", kind="Service",
                    name=lambda payload: "{}-dashboard".format(payload["data"]["name"])
                ),
            ]
        }
    }
]

rulesdata = endpoint_rulesdata + ws_app_rulesdata + secret_rulesdata
