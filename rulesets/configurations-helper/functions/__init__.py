import os

import pykube
import yaml

from k8s_functions import K8sObjectsQuery, k8s_subject, k8s_event_create, K8sObjectCreate, k8s_object

import pprint
import copy
from datetime import datetime, timezone

def _hashed(name, *args, length=10):
    import hashlib
    hash = ""
    for arg in args:
        hash += pprint.pformat(arg)
    return "{}-{}".format(name, hashlib.md5(hash.encode("utf8")).hexdigest()[:length])


class CreateConfigMap(K8sObjectCreate):

    def execute(self, provider=None, **kwargs):

        if provider is None:
            provider = self.payload["object"]
        data = provider["spec"].get("data", {})
        provider_name = provider["metadata"]["name"]
        namespace = provider["metadata"]["namespace"]
        cm_name = k8s_subject(provider).get("cm_name")
        cm = {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {
                "name": cm_name,
                "namespace": namespace,
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


def _update_configuration(instance, configuration, obj,
                          applied_patches_dest: list, status_dest: dict, _logs=[]):

    configuration_hash = k8s_subject(configuration).get("cfgp_hash").split("-")[-1]

    # is this configuration already applied
    try:
        prev_hash = k8s_subject(obj).get("_config__{}".format(configuration.get("metadata").get("name")))
        if prev_hash == configuration_hash:
            _logs.append("configuration already updated... skip")
            return
    except AttributeError:
        pass

    if applied_patches_dest is None:
        applied_patches_dest = []

    cm_name = _hashed(
        configuration["metadata"]["name"],
        configuration["spec"].get("data", {}),
    )
    mount_path = "/krules/config/" + "/".join(configuration.get("spec").get("key").split("."))
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
                    "containers": copy.deepcopy(
                        obj.obj.get("spec").get("template").get("spec").get("containers", [])),
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

        # preserve list elements in container section
        conf = configuration["spec"]["container"]
        for k, v in target.items():
            if isinstance(v, type([])) and k in conf:
                if k == "env":
                    target_d = {d["name"]: d for d in target[k]}
                    conf_d = {d["name"]: d for d in conf[k]}
                    env = []
                    all_names = set(list(target_d.keys())+list(conf_d.keys()))
                    for name in all_names:
                        if name in conf_d:
                            env.append(conf_d[name])
                        else:
                            env.append(target_d[name])
                    conf[k] = env
                else:
                    if v not in conf[k]:
                        for el in v:
                            if el not in conf[k]:
                                conf[k].append(el)

        target.update(conf)
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

    extra_volumes = configuration["spec"].get("extraVolumes", [])
    volumes.extend(extra_volumes)

    applied_patches_dest.append(patch)

    try:
        obj.patch(patch)
        k8s_subject(obj).set("_config__{}".format(configuration.get("metadata").get("name")), configuration_hash,
                             use_cache=False, muted=True)
        status_dest.update({
            obj.name: {
                "applied": True,
                "lastTransitionTime": datetime.now(timezone.utc).astimezone().isoformat()
            }
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
        status_dest.update({
             obj.name: {
                "applied": False,
                "reason": str(ex),
                "lastTransitionTime": datetime.now().isoformat()
             }
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


class PatchExistingServices(K8sObjectsQuery):

    def execute(self, **kwargs):

        configuration = kwargs.get("configuration")
        prepare_status_out = kwargs.get("prepare_status_out")

        prepare_status_out_ref = self.payload[prepare_status_out] = {}
        applied_patches_ref = self.payload["_appliedPatches"] = []
        log_ref = self.payload["_patch_existing_services_logs"] = []

        selector = {}
        for k, v in self.payload["object"]["spec"].get("appliesTo", {}).items():
            if isinstance(v, type([])):
                selector[f"{k}__in"] = set(v)
            else:
                selector[k] = v

        super().execute(
            apiversion="serving.knative.dev/v1", kind="Service",
            namespace=self.subject.get_ext("namespace"),
            selector=selector,
            foreach=lambda obj: (
                _update_configuration(
                    instance=self,
                    configuration=configuration,
                    obj=obj,
                    applied_patches_dest=applied_patches_ref,
                    status_dest=prepare_status_out_ref,
                    _logs=log_ref
                )
            ),
        )


class PatchService(K8sObjectsQuery):

    def _update_configuration_if_match(self, configuration, applied_patches_dest, stauts_dest, _logs):

        # check if already applied
        if "_config__{}".format(configuration.name) in self.subject:
            _logs.append(f"{configuration.name} already applied")
            return

        appliesTo = configuration.obj["spec"].get("appliesTo", {})
        match = True
        labels = k8s_object(self.subject).get("metadata", {}).get("labels", {})
        for k, v in appliesTo.items():
            if k not in labels:
                match = False
                break
            if isinstance(v, type([])):
                if labels[k] not in v:
                    match = False
                    break
            else:
                if labels[k] != v:
                    match = False
                    break

        _logs.append(f"match: {match}")

        if match:
            obj = pykube.object_factory(
                self.payload["_k8s_api_client"],
                self.subject.get_ext("apiversion"), self.subject.get_ext("kind")).\
                    objects(self.payload["_k8s_api_client"]).filter(
                        namespace=self.subject.get_ext("namespace")
                    ).get(name=self.subject.get_ext("name"))

            _update_configuration(
                instance=self,
                configuration=configuration.obj,
                obj=obj,
                applied_patches_dest=applied_patches_dest,
                status_dest=stauts_dest,
                _logs=_logs
            )

    def execute(self, **kwargs):

        prepare_status_out = kwargs.get("prepare_status_out")

        prepare_status_out_ref = self.payload[prepare_status_out] = {}
        applied_patches_ref = self.payload["_appliedPatches"] = []
        log_ref = self.payload["_patch_service_logs"] = []

        super().execute(
            apiversion="krules.airspot.dev/v1alpha1", kind="ConfigurationProvider",
            namespace=self.subject.get_ext("namespace"),
            foreach=lambda obj: self._update_configuration_if_match(
                configuration=obj,
                applied_patches_dest=applied_patches_ref,
                stauts_dest=prepare_status_out_ref,
                _logs=log_ref
            )
        )