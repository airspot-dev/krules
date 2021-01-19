
import copy
import time
from datetime import datetime, timezone
import os
import functools, operator


import yaml
from krules_core.base_functions import *

from krules_core import RuleConst as Const

from k8s_functions import *

from krules_core.event_types import SUBJECT_PROPERTY_CHANGED
from krules_env import publish_proc_events_all

rulename = Const.RULENAME
subscribe_to = Const.SUBSCRIBE_TO
ruledata = Const.RULEDATA
filters = Const.FILTERS
processing = Const.PROCESSING

#LBL_INJECT = "krules.airspot.dev/injection"

DEFAULT_BROKER = "default"
PROCEVENTS_BROKER = "procevents"
PROCEVENTS_TRIGGER = "procevents-trigger"


from functions import (
    PatchExistingServices,
    PatchService,
    CreateConfigMap,
    _hashed
)

from krules_core.providers import proc_events_rx_factory
import pprint
proc_events_rx_factory().subscribe(
    on_next=pprint.pprint
)
# proc_events_rx_factory().subscribe(
#     on_next=publish_proc_events_all,
# )



create_configuration_rulesdata = [
    """
    On configuration update set a property hashing only significant values to react
    """,
    {
        rulename: "on-configuration-change-set-properties-and-status",
        subscribe_to: [
            "k8s.resource.add",
            "k8s.resource.update",
        ],
        ruledata: {
            filters: [
                Filter(  # check kind
                    lambda subject: (
                            subject.get_ext("kind") == "ConfigurationProvider"
                    )
                ),
            ],
            processing: [
                SetSubjectProperty("cfgp_hash", lambda self: (
                    _hashed(
                        self.subject.get_ext("name"),
                        self.payload["object"]["spec"].get("data", {}),
                        self.payload["object"]["spec"].get("container", {}),
                    )
                ), use_cache=False),
                SetSubjectProperty("cm_name", lambda self: (
                    _hashed(
                        self.subject.get_ext("name"),
                        self.payload["object"]["spec"]["data"],
                    )
                ), use_cache=False),
                K8sObjectUpdate(lambda payload: {
                        "status": {
                            "applied_to": ", ".join(
                                 "%s:%s" % i for i in payload["object"]["spec"].get("appliesTo", {}).items()
                             )
                        }
                }, subresource="status")
            ]
        }
    },
    """
    On new configmap (name) create it
    """,
    {
       rulename: "on-new-cm-create",
       subscribe_to: SUBJECT_PROPERTY_CHANGED,
       ruledata: {
           filters: [
               OnSubjectPropertyChanged("cm_name"),
               K8sObjectsQuery(  # cm does not already exists
                   apiversion="v1", kind="ConfigMap",
                   returns=lambda payload: (
                       lambda qobjs: qobjs.get_or_none(name=payload["value"]) is None
                   )
               )
           ],
           processing: [
               SetPayloadProperty("object", lambda subject: k8s_object(subject, renew=True)),
               CreateConfigMap(provider=lambda payload: payload["object"]),
           ]
       }
    },
    """
    On new configmap (name) remove the old one
    """,
    {
        rulename: "on-new-cm-remove-old",
        subscribe_to: SUBJECT_PROPERTY_CHANGED,
        ruledata: {
            filters: [
                OnSubjectPropertyChanged("cm_name", old_value=lambda v: v is not None),
            ],
            processing: [
                K8sObjectDelete(
                    apiversion="v1", kind="ConfigMap",
                    namespace=lambda subject: subject.get_ext("namespace"),
                    name=lambda payload: payload["old_value"]
                )
            ]
        }
    },
    """
    On generated config map deleted force the creation of a new one
    """,
    {
        rulename: "on-generated-cm-deleted",
        subscribe_to: "k8s.resource.delete",
        ruledata: {
            filters: [
                PayloadMatchOne('$._event_info.kind', "ConfigMap"),
                PayloadMatchOne('object.metadata.labels."config.krules.airspot.dev/provider"',
                                payload_dest="provider_name")
            ],
            processing: [
                K8sObjectsQuery(
                    apiversion="krules.airspot.dev/v1alpha1",
                    kind="ConfigurationProvider",
                    namespace=lambda subject: subject.get_ext("namespace"),  # TODO: should be implicit !
                    returns=lambda payload: lambda qobjs: (
                        payload.setdefault("provider_object", qobjs.get(name=payload["provider_name"]).obj)
                    )
                ),
                CreateConfigMap(provider=lambda payload: payload.get("provider_object"))
            ]
        }
    }
]

apply_confugaration_rulesdata = [
    """
    On configuration change inject configuration to existing services
    """,
    {
        rulename: "on-configuration-change-configure-existing-services",
        subscribe_to: SUBJECT_PROPERTY_CHANGED,
        ruledata: {
            filters: [
                OnSubjectPropertyChanged("cfgp_hash"),
            ],
            processing: [
                Process(
                    # workaround we're too fast (TODO: still necessary?)
                    lambda: time.sleep(1)
                ),
                SetPayloadProperty("object", lambda subject: k8s_object(subject, renew=True)),
                PatchExistingServices(
                    configuration=lambda payload: payload["object"],
                    prepare_status_out="_preparedStatus"
                ),
                # K8sObjectUpdate(
                #     lambda payload: {
                #         "status": {
                #             "services": payload["_preparedStatus"],
                #         }
                #     },
                #     subresource="status"
                # )
            ]
        }
    },
    """
    On new service set lables hash and dispose configuration
    """,
    {
        rulename: "on-new-service-dispose-configuration",
        subscribe_to: [
            "k8s.resource.add",
        ],
        ruledata: {
            filters: [
                Filter(  # check kind
                    lambda subject:
                         subject.get_ext("kind") == "Service"
                ),
                Filter(
                    lambda payload:
                        "labels" in payload["object"].get("metadata", {})
                )
            ],
            processing: [
                SetSubjectProperty("labels_hash", lambda payload: _hashed(
                    "lbls", payload["object"]["metadata"].get("labels", {})
                ), use_cache=True, muted=True),
                Route(
                    event_type="do-patch-service-request"
                )
            ]
        }
    },
    """
    On service update check for lables mutations eventually dispose patch
    """,
    {
        rulename: "on-service-update-dispose-configuration",
        subscribe_to: "k8s.resource.update",
        ruledata: {
            filters: [
                Filter(
                    lambda subject:
                         subject.get_ext("kind") == "Service"
                ),
                Filter(
                    lambda subject:
                        "labels_hash" in subject
                ),
                Filter(
                    lambda self: _hashed(
                        "lbls", self.payload["object"]["metadata"].get("labels", {})
                    ) != self.subject.get("labels_hash")
                ),
            ],
            processing: [
                SetSubjectProperty("labels_hash", lambda payload: _hashed(
                    "lbls", payload["object"]["metadata"].get("labels", {})
                ), use_cache=False, muted=True),
                Route(
                    event_type="do-patch-service-request"
                )
            ]
        }
    },
    """
    Patch the service finding applicable configurations
    """,
    {
        rulename: "do-patch-service",
        subscribe_to: "do-patch-service-request",
        ruledata: {
            processing: [
                PatchService(
                    prepare_status_out="_preparedStatus"
                ),
                # K8sObjectUpdate(
                #     lambda payload: {
                #         "status": {
                #             "services": payload["_preparedStatus"],
                #         }
                #     },
                #     subresource="status"
                # )
            ]
            ,
        }
    },
]

rulesdata = create_configuration_rulesdata + apply_confugaration_rulesdata