#from k8s_functions import K8sObjectsQuery
import copy

from k8s_functions import K8sObjectsQuery
from krules_core import RuleConst as Const
from krules_core.base_functions import *

from cfgp import apply_configuration
from . import MakePatch

rulename = Const.RULENAME
subscribe_to = Const.SUBSCRIBE_TO
ruledata = Const.RULEDATA
filters = Const.FILTERS
processing = Const.PROCESSING


class ApplyConfiguration(K8sObjectsQuery):

    @staticmethod
    def _update_configuration_if_match(configuration, dest, root_expr, preserve_name, _log=[]):

        appliesTo = configuration["spec"].get("appliesTo", {})
        match = True
        labels = dest.get("metadata", {}).get("labels", {})
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
            apply_configuration(configuration=configuration, dest=dest,
                                root_expr=root_expr, preserve_name=preserve_name, _log=_log)


    def execute(self, root_expr, preserve_name, **kwargs):

        # src = self.payload["request"]["object"]
        # self.payload["__mutated_object"] = copy.deepcopy(src)
        self.payload["_log"] = []

        super().execute(
            apiversion="krules.airspot.dev/v1alpha1", kind="ConfigurationProvider",
            namespace=self.payload["request"]["namespace"],
            foreach=lambda obj: self._update_configuration_if_match(
                configuration=obj.obj,
                dest=self.payload["__mutated_object"],
                root_expr=root_expr,
                preserve_name=preserve_name,
                _log=self.payload["_log"]
            )
        )


rulesdata = [
    """
    Apply configurations to pods only when not owned by other objects
    """,
    {
        rulename: "apply-configuration-to-pod",
        subscribe_to: ["mutate-pod-create"],
        ruledata: {
            filters: [
                PayloadMatchOne(
                    "$.request.object.metadata.ownerReferences",
                    match_value=lambda v: v is None or len(v) == 0
                )
            ],
            processing: [
                ApplyConfiguration(
                    root_expr="$",
                    preserve_name=True,
                )
            ]
        }
    },
    """
    Apply configurations to deployments only when not owned by other objects
    """,
    {
        rulename: "apply-configuration-to-deployment",
        subscribe_to: ["mutate-deployment-create"],
        ruledata: {
            filters: [
                PayloadMatchOne(
                    "$.request.object.metadata.ownerReferences",
                    match_value=lambda v: v is None or len(v) == 0
                )
            ],
            processing: [
                ApplyConfiguration(
                    root_expr="$.spec.template",
                    preserve_name=True,
                )
            ]
        }
    },
    """
    Apply configurations to knative services (revisions)
    """,
    {
        rulename: "apply-configuration-to-kservice",
        subscribe_to: ["mutate-kservice-create"],
        ruledata: {
            processing: [
                ApplyConfiguration(
                    root_expr="$.spec.template",
                    preserve_name=True,
                )
            ]
        }
    },
]