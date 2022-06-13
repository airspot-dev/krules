import os

import pykube
import yaml

from krules_core import RuleConst as Const
from krules_core.base_functions import *
from krules_core.event_types import *
from krules_core.providers import subject_factory

import k8s

rulename = Const.RULENAME
subscribe_to = Const.SUBSCRIBE_TO
ruledata = Const.RULEDATA
filters = Const.FILTERS
processing = Const.PROCESSING

ruleset_config: dict = configs_factory()["rulesets"][os.environ["CE_SOURCE"]]


class K8sObjectSubjectMatch(SubjectNameMatch):

    def execute(self, *args, **kwargs):

        return super().execute(
            "^k8s:/apis/(?P<api_version>.+)/namespaces/(?P<namespace>.+)/(?P<resources>.+)/(?P<name>.+)$"
        )


class UpdateServices(RuleFunctionBase):

    def execute(self, configuration):
        config = pykube.KubeConfig.from_env()
        api = pykube.HTTPClient(config)

        selector = {}
        for k, v in configuration["spec"].get("appliesTo", {}).items():
            if isinstance(v, type([])):
                selector[f"{k}__in"] = set(v)
            else:
                selector[k] = v
        self.payload["_selector"] = selector
        for K8sClass in [k8s.KService, pykube.Deployment]:
            qobjs = K8sClass.objects(api).filter(selector=selector)

            _matches = []
            for obj in qobjs:
                if len(obj.obj["metadata"].get("ownerReferences", [])) > 0:
                    continue
                subject = subject_factory(f"k8s:/apis/{obj.version}/namespaces/{obj.namespace}/services/{obj.name}")
                _matches.append(subject.name)
                labels = obj.obj["metadata"].get("labels", {})
                image_base = subject.get("image_base")

                subject.set("build_source", compose_build_source(
                    api=api, image_base=image_base, labels=labels
                ), use_cache=False)

        self.payload["_matches"] = _matches


def compose_build_source(api, image_base, labels, log=[]):
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


class SetBuildSource(RuleFunctionBase):

    def execute(self):
        config = pykube.KubeConfig.from_env()
        api = pykube.HTTPClient(config)

        labels = self.subject.get("labels")
        image_base = self.subject.get("image_base")

        self.payload["_log"] = []
        build_source = compose_build_source(api, image_base, labels, self.payload["_log"])

        self.subject.set("build_source", build_source, use_cache=False)


class SetK8sObjectProperties(RuleFunctionBase):

    def execute(self):
        subject = subject_factory(f"k8s:{self.subject.name}")

        annotations = self.payload["metadata"].get("annotations", {})

        props = yaml.load(
            annotations.setdefault("krules.dev/props", "{}"),
            Loader=yaml.SafeLoader
        )
        for prop in props:
            subject.set(prop, props[prop])

        subject.set("labels", self.payload.get("metadata", {}).get("labels"))


rulesdata = [
    {
        rulename: "on-k8s-ojbect-add-update-set-subject",
        subscribe_to: [
            "dev.knative.apiserver.resource.update",
            "dev.knative.apiserver.resource.add",
        ],
        ruledata: {
            filters: [
                Filter(
                    lambda payload:
                    payload["apiVersion"] == "serving.knative.dev/v1" and payload["kind"] == "Service"
                    or
                    payload["apiVersion"] == "apps/v1" and payload["kind"] == "Deployment" and
                    len(payload["metadata"].get("ownerReferences", [])) == 0
                )
            ],
            processing: [
                SetK8sObjectProperties(),
            ],
        }
    },
    {
        rulename: "on-k8s-object-delete-flush-subject",
        subscribe_to: [
            "dev.knative.apiserver.resource.delete",
        ],
        ruledata: {
            processing: [
                Process(
                    lambda subject: subject_factory(f"k8s:{subject.name}").flush()
                )
            ],
        }
    },
    {
        rulename: "on-k8s-obj-update-set-build-source",
        subscribe_to: SUBJECT_PROPERTY_CHANGED,
        ruledata: {
            filters: [
                OnSubjectPropertyChanged("labels"),
                K8sObjectSubjectMatch(),
                Filter(
                    lambda payload:
                    payload["subject_match"]["api_version"] == "apps/v1"
                    and payload["subject_match"]["resources"] == "deployments"
                    or
                    payload["subject_match"]["api_version"] == "serving.knative.dev/v1"
                    and payload["subject_match"]["resources"] == "services"
                ),
                Filter(
                    lambda payload:
                    "krules.dev/app" in payload["value"]
                ),
            ],
            processing: [
                SetBuildSource()
            ]
        }
    },
    {
        rulename: "on-cfgp-update-services",
        subscribe_to: [
            "dev.knative.apiserver.resource.update",
            "dev.knative.apiserver.resource.add",
            "dev.knative.apiserver.resource.delete",
        ],
        ruledata: {
            filters: [
                Filter(
                    lambda payload:
                    payload["kind"] == "ConfigurationProvider"
                ),
            ],
            processing: [
                UpdateServices(
                    configuration=lambda payload: payload
                )
            ],
        }
    },
    {
        rulename: "dispatch-build-ext",
        subscribe_to: SUBJECT_PROPERTY_CHANGED,
        ruledata: {
            filters: [
                OnSubjectPropertyChanged("build_source")
            ],
            processing: [
                Route(dispatch_policy=DispatchPolicyConst.DIRECT)
            ],
        }
    },

]
