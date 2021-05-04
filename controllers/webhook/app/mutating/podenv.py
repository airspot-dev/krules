import copy

from krules_core import RuleConst as Const
from krules_core.base_functions import *
from k8s_functions import K8sObjectsQuery

from . import MakePatch
import jsonpath_rw_ext as jp

rulename = Const.RULENAME
subscribe_to = Const.SUBSCRIBE_TO
ruledata = Const.RULEDATA
filters = Const.FILTERS
processing = Const.PROCESSING


class SetPodEnvVar(RuleFunctionBase):

    def execute(self, name, value, containers_path="$.spec.containers", update_existing=False, **kwargs):
        if len(jp.match1(containers_path, self.payload["request"]["object"])) == 0:
            return

        # we don't want to deep copy the whole object, just the containers[0] part
        dst = self.payload["__mutated_object"]
        env = jp.match1(containers_path, dst)[0].setdefault("env", [])
        found = False
        for i in env:
            if i.get("name") == name:
                if update_existing:
                    i["value"] = value
                found = True
                break
        if not found:
            env.append({
                "name": name,
                "value": value
            })


rulesdata_sinks = [
    """
    Ensure K_SINK for all pods
    """,
    {
        rulename: "mutate-pod-env-default-sink",
        subscribe_to: ["mutate-pod-create", "mutate-pod-update"],
        ruledata: {
            filters: [
                PayloadMatchOne("$.request.object.spec.containers[0].env[?@.name='K_SINK']",
                                match_value=None),
                K8sObjectsQuery(
                    apiversion="eventing.knative.dev/v1",
                    kind="Broker",
                    namespace=lambda payload: payload["request"].get("namespace"),
                    returns=lambda payload:
                        lambda qobjs: payload.setdefault(
                            "__broker_ref", qobjs.get_or_none(name="default")
                        )
                ),
                Filter(lambda payload: payload["__broker_ref"] is not None),
            ],
            processing: [
                SetPodEnvVar(
                    "K_SINK",
                    lambda payload: payload["__broker_ref"].obj["status"].get("address", {}).get("url")
                )
            ]
        }
    },
    """
    Ensure K_PROCEVENTS_SINK for pods having PUBLISH_PROCEVENTS_LEVEL >= 1
    It also set a default value for PUBLISH_PROCEVENTS_MATCH (1: got_errors=true, 2: *)
    """,
    {
        rulename: "mutate-pod-env-procevents-sink",
        subscribe_to: ["mutate-pod-create", "mutate-pod-update"],
        ruledata: {
            filters: [
                PayloadMatchOne("$.request.object.spec.containers[0].env[?@.name='PUBLISH_PROCEVENTS_LEVEL'].value",
                                match_value=lambda v: v is not None and str(v) in ["1", "2"],
                                payload_dest="__procevents_match_level"),
                K8sObjectsQuery(
                    apiversion="eventing.knative.dev/v1",
                    kind="Broker",
                    namespace=lambda payload: payload["request"].get("namespace"),
                    returns=lambda payload:
                    lambda qobjs: payload.setdefault(
                        "__broker_procevents_ref", qobjs.get_or_none(name="procevents")
                    )
                ),
                Filter(lambda payload: payload["__broker_procevents_ref"] is not None),
            ],
            processing: [
                SetPodEnvVar(
                    "K_PROCEVENTS_SINK",
                    lambda payload: payload["__broker_procevents_ref"].obj["status"].get("address", {}).get("url"),
                    update_existing=False
                ),
                SetPodEnvVar(
                    "PUBLISH_PROCEVENTS_MATCH",
                    lambda payload: str(payload["__procevents_match_level"]) == "1" and "got_errors=true" or "*",
                    update_existing=False
                )
            ]
        }
    }
]

rulesdata_ce_source = [
    """
    for unowned pods we get the pod's name
    """,
    {
        rulename: "mutate-pod-env-ce-source-unowned",
        subscribe_to: ["mutate-pod-create"],
        ruledata: {
            filters: [
                PayloadMatchOne(
                    "$.request.object.metadata.ownerReferences",
                    match_value=lambda v: v is None or len(v) == 0
                ),
                PayloadMatchOne("$.request.object.spec.containers[0].env[?@.name='CE_SOURCE']",
                                match_value=None),
            ],
            processing: [
                SetPodEnvVar(
                    "CE_SOURCE",
                    lambda payload: payload["request"]["object"]["metadata"]["name"],
                ),
            ]
        }
    },
    """
    for unowned pods we get the pod's name
    """,
    {
        rulename: "mutate-pod-env-ce-source-kservice",
        subscribe_to: ["mutate-pod-create"],
        ruledata: {
            filters: [
                PayloadMatchOne(
                    "$.request.object.metadata.labels",
                    match_value=lambda labels: "serving.knative.dev/revision" in labels
                ),
                PayloadMatchOne("$.request.object.spec.containers[0].env[?@.name='CE_SOURCE']",
                                match_value=None),
            ],
            processing: [
                SetPodEnvVar(
                    "CE_SOURCE",
                    lambda payload: payload["request"]["object"]["metadata"]["labels"]["serving.knative.dev/revision"],
                ),
            ]
        }
    },
    """
    for unowned pods we get the pod's name
    """,
    {
        rulename: "mutate-pod-env-ce-source-deployment",
        subscribe_to: ["mutate-deployment-create"],
        ruledata: {
            filters: [
                PayloadMatchOne(
                    "$.request.object.metadata.ownerReferences",
                    match_value=lambda v: v is None or len(v) == 0
                ),
                PayloadMatchOne("$.request.object.spec.template.spec.containers[0].env[?@.name='CE_SOURCE']",
                                match_value=None),
            ],
            processing: [
                SetPodEnvVar(
                    "CE_SOURCE",
                    lambda payload: payload["request"]["object"]["metadata"]["name"],
                    containers_path="spec.template.spec.containers",
                ),
            ]
        }
    }

]

rulesdata = rulesdata_sinks + rulesdata_ce_source