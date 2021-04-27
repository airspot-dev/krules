import copy

from krules_core import RuleConst as Const
from krules_core.base_functions import *
from k8s_functions import K8sObjectsQuery

from . import MakePatch

rulename = Const.RULENAME
subscribe_to = Const.SUBSCRIBE_TO
ruledata = Const.RULEDATA
filters = Const.FILTERS
processing = Const.PROCESSING


class MakePodEnvVarPatch(MakePatch):

    def execute(self, name, value, update_existing=False, **kwargs):
        if len(self.payload["request"]["object"]["spec"]["containers"]) == 0:
            return

        # we don't want to deep copy the whole object, just the containers[0] part
        src = {
            "spec": {
                "containers": self.payload["request"]["object"]["spec"]["containers"]
            }
        }

        dst = copy.deepcopy(src)
        env = dst["spec"]["containers"][0].setdefault("env", [])
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
        super().execute(src, dst)


rulesdata = [
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
                MakePodEnvVarPatch(
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
                MakePodEnvVarPatch(
                    "K_PROCEVENTS_SINK",
                    lambda payload: payload["__broker_procevents_ref"].obj["status"].get("address", {}).get("url"),
                    update_existing=False
                ),
                MakePodEnvVarPatch(
                    "PUBLISH_PROCEVENTS_MATCH",
                    lambda payload: str(payload["__procevents_match_level"]) == "1" and "got_errors=true" or "*",
                    update_existing=False
                )
            ]
        }
    }
]