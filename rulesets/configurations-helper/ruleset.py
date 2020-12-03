import copy
from datetime import datetime, timezone
import os

import yaml
from krules_core.base_functions import *

from krules_core import RuleConst as Const

from k8s_functions import *

from krules_core.types import SUBJECT_PROPERTY_CHANGED
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

from krules_core.providers import proc_events_rx_factory
import pprint

proc_events_rx_factory().subscribe(
    on_next=pprint.pprint
)


proc_events_rx_factory().subscribe(
    on_next=publish_proc_events_all,
)

def _hashed(name, *args, length=10):
    import hashlib
    hash = ""
    for arg in args:
        hash += pprint.pformat(arg)
    return "{}-{}".format(name, hashlib.md5(hash.encode("utf8")).hexdigest()[:length])


class _CreateConfigMap(K8sObjectCreate):

    def execute(self, provider=None, **kwargs):

        if provider is None:
            provider = self.payload["object"]
        data = provider["spec"]["data"]
        provider_name = provider["metadata"]["name"]
        namesapce = provider["metadata"]["namespace"]
        cm_name = self.payload["cm_name"]
        cm = {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {
                "name": cm_name,
                "namespace": namesapce,
                "labels": {
                    #"config.krules.airspot.dev/provided": "provided",
                    "config.krules.airspot.dev/provider": provider_name,
                },
            },
            "data": {
                "{}.yaml".format(cm_name.replace("-", "_")): yaml.dump(data)
            }
        }

        super().execute(cm)


create_configuration_rulesdata = [
    """
    On configurations add/update create configmap
    #############################################
    """,
    {
        rulename: "on-configuration-change-create-cm",
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
                Filter(  # set cm name in payload
                    lambda self: (
                        self.payload.setdefault(
                            "cm_name", _hashed(
                                self.subject.get_ext("name"),
                                self.payload["object"]["spec"]["data"],
                            )
                        )
                    )
                ),
                K8sObjectsQuery(  # cm does not already exists
                    apiversion="v1", kind="ConfigMap",
                    returns=lambda payload: (
                        lambda qobjs: qobjs.get_or_none(name=payload["cm_name"]) is None
                    )
                )
            ],
            processing: [
                _CreateConfigMap(),
                SetSubjectProperty("cm_name", lambda payload: payload["cm_name"], use_cache=False)
            ]
        },
    },
    """
    On configuration update set a property hashing only significant values to react
    """,
    {
        rulename: "on-configuration-change-set-hash-property",
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
            ]
        }
    },
    """,
    On new configmap remove the old one
    """,
    {
        rulename: "on-new-cm-remove-old",
        subscribe_to: SUBJECT_PROPERTY_CHANGED,
        ruledata: {
            filters: [
                OnSubjectPropertyChanged("cm_name", old_value=lambda v: v is not None)
            ],
            processing: [
                K8sObjectDelete(
                    apiversion="v1", kind="ConfigMap",
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
                PayloadMatchOne("$._event_info.kind", "ConfigMap"),
                PayloadMatchOne("object.metadata.labels.config\.krules\.airspot\.dev/provider",
                                payload_dest="provider_name")
            ],
            processing: [
                K8sObjectsQuery(
                    api_version="krules.airspot.dev/v1alpha1",
                    kind="ConfigurationProvider",
                    returns=lambda payload: lambda qobjs: (
                        payload.setdefault("provider_object", qobjs.get(name=payload["provider_name"]).obj)
                    )
                ),
                _CreateConfigMap(provider=lambda payload: payload.get("provider_object"))
            ]
        }
    }
]

def _update_configuration(instance, configuration, obj, applied_patches_dest: list, status_dest: list, _logs=[]):

    new_name = "{}-{}".format(
                        obj.name,
                        k8s_subject(configuration).get("cfgp_hash").split("-")[-1]
                    )

    # is this configuration already applied
    if obj.obj.get("spec").get("template").get("metadata").get("name") == new_name:
        return

    if applied_patches_dest is None:
        applied_patches_dest = []

    cm_name = _hashed(
        configuration["metadata"]["name"],
        configuration["spec"]["data"],
    )
    mount_path = "/config/krules/"+"/".join(configuration.get("spec").get("key").split("."))
    _obj = copy.deepcopy(obj.obj)
    _obj_spec = _obj.get("spec").get("template").get("spec")
    patch = {
        "spec": {
            "template": {
                "metadata": {
                    "name": "{}-{}".format(
                        obj.name,
                        k8s_subject(configuration).get("cfgp_hash").split("-")[-1]
                    )
                },
                "spec": {
                    "containers": copy.deepcopy(obj.obj.get("spec").get("template").get("spec").get("containers", [])),
                    "volumes": copy.deepcopy(obj.obj.get("spec").get("template").get("spec").get("volumes", []))
                }
            },
        }
    }
    if configuration.get("spec").get("container") is not None:
        # get target image name
        container_name = configuration["spec"]["container"].get("name")
        # if no name get the first element
        # it's ok to get an exception if no containers are found
        target = None
        if container_name is None:
            target = patch["spec"]["template"]["spec"]["containers"][0]
        else:
            container: dict
            for container in patch["spec"]["template"]["spec"]["containers"]:
                if container.get("name") == container_name:
                    target = container
        if target is None:
            raise ValueError("container {} not found".format(container_name))

        # volume mount
        mounts = target.setdefault("volumeMounts", [])
        found = False
        for m in mounts:
            if m["name"] == configuration.get("metadata").get("name"):
                found = True
                break
        if not found:
            mounts.append({
                    "name": configuration.get("metadata").get("name"),
                    "mountPath": mount_path
                })

        target.update(configuration["spec"]["container"])
        _logs.append({"target": target})

    else:
        _logs.append("configuration spec/container is None")
    # volumes
    cm_volume = {
        "name": configuration.get("metadata").get("name"),
        "configMap": {
            "name": cm_name
        }
    }

    found = False
    volumes = patch["spec"]["template"]["spec"].get("volumes", [])
    volume: dict
    for volume in volumes:
        if volume["name"] == configuration.get("metadata").get("name"):
            volume.update(cm_volume)
            found = True
            break
    if not found:
        volumes.append(cm_volume)

    applied_patches_dest.append(patch)

    try:
        obj.patch(patch)
        status_dest.append({
            "service": obj.name,
            "applied": True,
            "lastTransitionTime": datetime.now(timezone.utc).astimezone().isoformat()
        })
        k8s_event_create(
            api=instance.payload.get("_k8s_api_client"),
            producer=configuration["metadata"]["name"],
            involved_object=obj.obj,
            action="ApplyConfiguration",
            message="Successful applied \"{}\" ConfigurationProvider to \"{}\" knative service".format(
                configuration["metadata"]["name"],
                obj.name
            ),
            reason="AppliedConfigurationProvider",
            type="Normal",
            reporting_component=os.environ["K_SERVICE"],
            reporting_instance=instance.rule_name,
            source_component=configuration["metadata"]["name"]
        )
    except Exception as ex:
        status_dest.append({
            "service": obj.name,
            "applied": False,
            "reason": str(ex),
            "lastTransitionTime": datetime.now().isoformat()
        })
        k8s_event_create(
            api=instance.payload.get("_k8s_api_client"),
            producer=configuration["metadata"]["name"],
            involved_object=obj.obj,
            action="ApplyConfiguration",
            message=str(ex),
            reason="FailedToApplyConfigurationProvider",
            type="Warning",
            reporting_component=os.environ["K_SERVICE"],
            reporting_instance=instance.rule_name,
            source_component=configuration["metadata"]["name"],
        )

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
                SetPayloadProperty("object", lambda subject: k8s_object(subject, renew=True)),
                SetPayloadProperty("appliedPatches", lambda: []),
                SetPayloadProperty("preparedStatus", lambda: []),
                SetPayloadProperty("_logs", lambda: []),
                K8sObjectsQuery(
                    apiversion="serving.knative.dev/v1", kind="Service",
                    namespace=lambda subject: subject.get_ext("namespace"),
                    selector=lambda payload: payload["object"]["spec"].get("appliesTo", {}),
                    foreach=lambda self: (
                        lambda obj: (
                            _update_configuration(
                                instance=self,
                                configuration=self.payload["object"],
                                obj=obj,
                                applied_patches_dest=self.payload["appliedPatches"],
                                status_dest=self.payload["preparedStatus"],
                                _logs=self.payload["_logs"],
                            )
                        )
                    )
                ),
                K8sObjectPatch(
                    lambda payload: {
                        "status": {
                            "services": payload["preparedStatus"],
                            "applied_to": ", ".join(
                                "%s=%s" % i for i in payload["object"]["spec"]
                                .get("appliesTo", {}).items()
                            )
                        }
                    },
                    subresource="status"
                )
            ]
        }
    },
    """
    On service create/update find configurations
    """,
    {
        rulename: "on-knative-service-configurations-check",
        subscribe_to: [
            "k8s.resource.add",
            "k8s.resource.update",
        ],
        ruledata: {
            filters: [
                Filter(  # check kind
                    lambda subject: (
                         subject.get_ext("kind") == "Service"
                    )
                ),
            ],
            processing: [
                K8sObjectsQuery(
                    apiversion="krules.airspot.dev/v1alpha1", kind="ConfigurationProvider",
                    namespace=lambda subject: subject.get_ext("namespace"),
                    foreach=lambda self: lambda obj: (
                        # simulates a configuration change
                        # all services are checked again
                        # this is to have the selector logic in one place only
                        self.router.route(
                            event_type="subject-property-changed",
                            subject=k8s_subject(obj),
                            payload={
                                "object": obj.obj,
                                "property_name": "cfgp_hash",
                                "value": k8s_subject(obj).get("cfgp_hash")
                            }
                        )
                    )

                )
            ]
        }
    }
]

rulesdata = create_configuration_rulesdata + apply_confugaration_rulesdata