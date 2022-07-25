import os
import pprint
import uuid
from datetime import datetime
from typing import Union

import pykube
import yaml
from pykube import Pod

from krules_core.base_functions import *
import k8s
from krules_core.providers import subject_factory
from krules_core.subject.storaged_subject import Subject

ruleset_config: dict = configs_factory()["rulesets"][os.environ["CE_SOURCE"]]


class IsDeployableTarget(RuleFunctionBase):
    """
    This resource is backed by a subject and refers to and image that can be built and deployed
    (Deployments or Knative services)
    """

    def execute(self, resource):
        return resource["apiVersion"] == "serving.knative.dev/v1" and resource["kind"] == "Service" \
               or \
               resource["apiVersion"] == "apps/v1" and resource["kind"] == "Deployment" and \
               len(resource["metadata"].get("ownerReferences", [])) == 0


class DeleteTaskRuns(RuleFunctionBase):

    def execute(self, service_name: str):
        config = pykube.KubeConfig.from_env()
        api = pykube.HTTPClient(config)

        qobjs = k8s.TaskRun.objects(api).filter(
            selector={
                "krules.dev/app": service_name
            }
        )
        for qobj in qobjs:
            qobj.delete()


def _compose_build_source(api, image_base, labels, log=[]):
    qobjs = k8s.ConfigurationProvider.objects(api).all()
    build_source = {
        "Dockerfile": f"FROM {image_base}"
    }
    for obj in qobjs:
        log.append(f"found cfgp: {obj.name}")
        configuration = obj.obj
        appliesTo = configuration["spec"].get("appliesTo", {})
        match = True
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

        if match:
            log.append(f"match {obj.name}")
            _build_ext = configuration["spec"].get("extensions", {}).get("build_ext", {})
            docker_adds = []
            for f in list(_build_ext.keys()):
                if f.startswith("^"):
                    f = f[1:]
                    _build_ext[f] = _build_ext.pop(f"^{f}")
                else:
                    docker_adds.append(f)

                if f in build_source:
                    build_source[f] += "\n" + _build_ext[f]
                else:
                    build_source[f] = _build_ext[f]
            if "Dockerfile" in build_source:
                for f in docker_adds:
                    build_source["Dockerfile"] += f"\nADD {f} /app/{f}"

    log.append(build_source)
    return build_source


class UpdateServices(RuleFunctionBase):

    def execute(self, configuration, service_target_property="build_source"):

        config = pykube.KubeConfig.from_env()
        api = pykube.HTTPClient(config)

        selector = {}
        for k, v in configuration["spec"].get("appliesTo", {}).items():
            if isinstance(v, type([])):
                selector[f"{k}__in"] = set(v)
            else:
                selector[k] = v
        _log = self.payload["_log"] = []
        _log.append(("selector", selector))
        for K8sClass in [k8s.KService, pykube.Deployment]:
            qobjs = K8sClass.objects(api).filter(namespace=api.config.namespace, selector=selector)

            for obj in qobjs:
                _log.append((repr(K8sClass), obj.name))
                if len(obj.obj["metadata"].get("ownerReferences", [])) > 0:
                    _log.append(("skip owned", obj.name))
                    continue
                subject = subject_factory(
                    #f"k8s:/apis/{obj.version}/namespaces/{obj.namespace}/{obj.endpoint}/{obj.name}")
                    f"krules:builder:{obj.namespace}:services:{obj.name}"
                )

                labels = obj.obj["metadata"].get("labels", {})

                if "image_base" in subject:
                    _log.append(("matched", subject.name))
                    image_base = subject.get("image_base")

                    subject.set(service_target_property, _compose_build_source(
                        api=api, image_base=image_base, labels=labels
                    ), use_cache=False)
                else:
                    _log.append(("skip missing image_base", subject.name))

        # self.router.route(
        #     "dbg-update-service",
        #     self.subject,
        #     self.payload
        # )


class SetBuildSource(RuleFunctionBase):

    def execute(self, target_property="build_source"):
        config = pykube.KubeConfig.from_env()
        api = pykube.HTTPClient(config)

        _log = self.payload["_log"] = []
        _log.append(f"subject: {self.subject.name}")

        _log.append([p for p in self.subject])
        labels = self.subject.get("labels")

        image_base = self.subject.get("image_base")

        build_source = _compose_build_source(api, image_base, labels, self.payload["_log"])

        self.subject.set(target_property, build_source, use_cache=False)


class CreateBuildSourceConfigMap(RuleFunctionBase):

    @staticmethod
    def _hashed(*args, length=10):
        import hashlib
        hash = ""
        for arg in args:
            hash += pprint.pformat(arg)
        return str(hashlib.md5(hash.encode("utf8")).hexdigest()[:length])

    def execute(self, payload_dest="cm_info"):
        if "_pykube_api" in self.payload:
            api = self.payload["_pykube_api"]
        else:
            config = pykube.KubeConfig.from_env()
            api = self.payload["_pykube_api"] = pykube.HTTPClient(config)

        source_hash = self._hashed(self.payload["value"])
        service_name = self.subject.name.split(":")[-1]
        cm_name = f"build-source-{service_name}-{source_hash}"
        cm = pykube.ConfigMap(api, {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {
                "name": cm_name,
                "labels": {
                    "krules.airspot.dev/type": "build-source",
                    "krules.airspot.dev/app": service_name,
                }
            },
            "data": self.payload["value"]
        })
        if not cm.exists():
            cm.create()

        self.payload[payload_dest] = {
            "cm_name": cm_name,
            "service_name": service_name
        }


class CreateTaskRun(RuleFunctionBase):

    def execute(self, config_name, service_name):

        if "_pykube_api" in self.payload:
            api = self.payload["_pykube_api"]
        else:
            config = pykube.KubeConfig.from_env()
            api = self.payload["_pykube_api"] = pykube.HTTPClient(config)

        spec = ruleset_config["taskRun"]["spec"]
        params = spec["params"]

        params.extend([
            {
                "name": "serviceName",
                "value": service_name,
            },
            {
                "name": "cmBuildSource",
                "value": config_name,
            }
        ])

        taskRun = {
            "apiVersion": "tekton.dev/v1beta1",
            "kind": "TaskRun",
            "metadata": {
                "generateName": "taskrun-build-and-push-",
                "annotations": {
                    "krules.dev/subject": self.subject.name,
                },
                "labels": {
                    "krules.dev/app": service_name
                }
            },
            "spec": spec,
            #                 "spec": {
            #                     "taskRef": {
            #                         "name": "build-and-push"
            #                     },
            # #                    "serviceAccountName": ruleset_config["taskRun"]["spec"]["serviceAccountName"],
            # #                    "params": params,
            #                 }
        }

        k8s.TaskRun(api, taskRun).create()


class OnTaskRunUpdatesSetSubject(RuleFunctionBase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from jsonpath_ng.ext import parse

        self.digest_jp_expr = parse('$.status.taskResults[?(name="digest")].value')
        self.status_condition_jp_expr = parse('$.status.conditions[?(type="Succeeded")]')
        self.status_completion_time_jp_expr = parse("$.status.completionTime")

    def execute(self, taskrun):

        subject = subject_factory(
            taskrun["metadata"]["annotations"]["krules.dev/subject"]
        )

        for match in self.digest_jp_expr.find(taskrun):
            subject.set("digest", match.value.strip(), use_cache=False)

        build_status = {}
        for match in self.status_condition_jp_expr.find(taskrun):
            match = match.value
            if "lastTransitionTime" in match:
                build_status["last_transition_time"] = match["lastTransitionTime"].replace("Z", "+00:00")
            build_status["message"] = match.get("message")
            build_status["reason"] = match.get("reason")
            build_status["status"] = match.get("status")

            error_logs = {}
            if match.get("status") == "False" and match.get("reason") == "Failed":
                # get failed step container
                if "_pykube_api" in self.payload:
                    api = self.payload["_pykube_api"]
                else:
                    config = pykube.KubeConfig.from_env()
                    api = self.payload["_pykube_api"] = pykube.HTTPClient(config)
                pod = Pod.objects(api).get(name=f"{taskrun['metadata']['name']}-pod")
                for step in taskrun.get("status", {}).get("steps", []):
                    if step.get("terminated", {}).get("reason") == "Error":
                        container_log = pod.logs(
                            container=step["container"]
                        )
                        error_logs[step["name"]] = container_log.split("\n")

            build_status["error_logs"] = error_logs

        for match in self.status_completion_time_jp_expr.find(taskrun):
            build_status["completion_time"] = match.value.replace("Z", "+00:00")

        if len(build_status):
            subject.build_status = build_status


class PatchKServiceImage(RuleFunctionBase):

    def execute(self, service_name, image):
        if "_pykube_api" in self.payload:
            api = self.payload["_pykube_api"]
        else:
            config = pykube.KubeConfig.from_env()
            api = self.payload["_pykube_api"] = pykube.HTTPClient(config)

        revision_name = f"{self.payload['subject_match']['service_name']}-{str(uuid.uuid4())[:5]}"

        obj = k8s.KService.objects(api).get(name=service_name)
        obj.obj["spec"]["template"]["metadata"]["name"] = revision_name
        obj.obj["spec"]["template"]["spec"]["containers"][0]["image"] = image
        obj.update()


class PatchDeploymentImage(RuleFunctionBase):

    def execute(self, deployment_name, image):
        if "_pykube_api" in self.payload:
            api = self.payload["_pykube_api"]
        else:
            config = pykube.KubeConfig.from_env()
            api = self.payload["_pykube_api"] = pykube.HTTPClient(config)

        obj = pykube.Deployment.objects(api).get(name=deployment_name)
        obj.obj["spec"]["template"]["spec"]["containers"][0]["image"] = image
        obj.update()


class UpdateSubjectConfigurationProperty(RuleFunctionBase):

    def execute(self, subject: Union[str, Subject], configuration: dict):

        if isinstance(subject, str):
            subject = subject_factory(subject)
        spec = configuration["spec"]
        p = {}
        if "configuration" in subject:
            p = subject.get("configuration")
        p["description"] = spec.get("description", "")
        p["data"] = spec.get("data", {})
        p["features"] = spec.get("features", [])
        p["extensions"] = spec.get("extensions", {})
        p["container"] = spec.get("container", {})
        p["extra_volumes"] = spec.get("extraVolumes")

        subject.set("configuration", p, use_cache=False)


class SubjectAnnotatePodInfo(RuleFunctionBase):

    def execute(self, resource: dict):

        api = resource.get("metadata", {}).get("annotations", {}).get("krules.dev/api")
        name = resource.get("metadata", {}).get("labels", {}) \
            .get("krules.dev/app", resource.get("metadata", {}).get("labels", {}).get("app"))
        namespace = resource.get("metadata", {}).get("namespace")

        subject: Subject
        revision: str
        subject = subject_factory(f"krules:builder:{namespace}:services:{name}")
        if api == "base":
            revision = name
        elif api == "knative":
            revision = resource.get("metadata", {}).get("labels", {}).get("serving.knative.dev/revision")
        else:
            return

        ready = len([condition for condition in resource.get("status", {}).get("conditions", [])
                     if condition["type"] == "Ready" and condition["status"] == "True"]) == 1

        pod_info = {
            "revision": revision,
            "ready": ready
        }
        failed_containers = {}
        if not ready:
            for container in resource.get("status", {}).get("containerStatuses", []):
                if container.get("ready") is False:
                    if "lastState" in container and "terminated" in container['lastState']:
                        if container['lastState']['terminated']['exitCode'] != 0:
                            message = container['lastState']['terminated']['reason']
                            if "message" in container['lastState']['terminated']:
                                message = container['lastState']['terminated']["message"]
                            failed_containers[container['name']] = message
                            pod_info['failed_containers'] = failed_containers
                            #break

        def _update_pods(cur_v):
            nonlocal self, resource
            if cur_v is None:
                cur_v = {}
            cur_v[resource["metadata"]["name"]] = pod_info
            return cur_v

        subject.set("pods", _update_pods, use_cache=False)
        # if len(failed_containers):
        #     subject.set("failed_containers", failed_containers)
        # else:
        #     subject.set("failed_containers", None)


class RemoveAnnotatedPodInfo(RuleFunctionBase):

    def execute(self, resource: dict):

        #api = resource.get("metadata", {}).get("annotations", {}).get("krules.dev/api")
        name = resource.get("metadata", {}).get("labels", {}) \
            .get("krules.dev/app", resource.get("metadata", {}).get("labels", {}).get("app"))
        namespace = resource.get("metadata", {}).get("namespace")

        subject: Subject
        revision: str
        subject = subject_factory(f"krules:builder:{namespace}:services:{name}")
        # if api == "base":
        #     # revision = name
        # elif api == "knative":
        #     subject = subject_factory(f"k8s:/apis/serving.knative.dev/v1/namespaces/{namespace}/services/{name}")
        #     # revision = resource.get("metadata", {}).get("labels", {}).get("serving.knative.dev/revision")
        # else:
        #     return

        def _delete_pod(cur_v):
            if cur_v is None:
                cur_v = {}
            del cur_v[resource["metadata"]["name"]]
            return cur_v

        subject.set("pods", _delete_pod, use_cache=False)


class SubjectAnnotateReplicaSetRevisionNo(RuleFunctionBase):

    def execute(self):

        namespace = self.payload.get("metadata", {}).get("namespace")
        name = self.payload.get("metadata", {}).get("mame")
        revision = self.payload.get("metadata", {}).get("annotations", {}).get("deployment.kubernetes.io/revision")
        subject = subject_factory(f"krules:builder:{namespace}:services:{name}")

        #assert "revision" is not None
        #assert "api" in subject and subject.get("api") == "base"

        def _annotate_rs_revision(cur_v):
            if cur_v is None:
                cur_v = {}
            cur_v[revision] = name

        subject.set("_rs_revisions", _annotate_rs_revision, muted=True)
