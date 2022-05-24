#from k8s_functions import K8sObjectsQuery
import copy

from k8s_functions import K8sObjectsQuery, ConfigurationProvider
from krules_core import RuleConst as Const
from krules_core.base_functions import *

from features import update_features_labels
from cfgp import apply_configuration, check_applies_to
from . import MakePatch

rulename = Const.RULENAME
subscribe_to = Const.SUBSCRIBE_TO
ruledata = Const.RULEDATA
filters = Const.FILTERS
processing = Const.PROCESSING


class ApplyConfiguration(K8sObjectsQuery):

    # @staticmethod
    # def _update_features_labels(configuration, dest):
    #
    #     if "labels" not in dest['metadata']:
    #         dest['metadata']['labels'] = {}
    #
    #     labels = dest['metadata']['labels']
    #     features = configuration.get("spec", {}).get("extensions", {}).get("features", {})
    #
    #     # clean previous
    #     # search for <feature>/...
    #     to_delete = []
    #     for feature_k in features:
    #         for label in labels:
    #             if label.startswith(f"{feature_k}/"):
    #                 to_delete.append(label)
    #     for label in to_delete:
    #         del labels[label]
    #
    #     # add features labels
    #     new_labels = {}
    #     for feature_k in features:
    #         for feature in features[feature_k]:
    #             new_labels[f"features.{feature_k}/{feature}"] = "enabled"  #features[feature_k][feature]
    #
    #     labels.update(new_labels)
    #
    #     return new_labels

    def _update_configuration_if_match(self, configuration, dest, root_expr, preserve_name, _log=[]):


        appliesTo = configuration["spec"].get("appliesTo", {})
        labels = dest.get("metadata", {}).get("labels", {})
        match = self.applies_to(appliesTo, labels)

        if match:
            features_labels = update_features_labels(configuration, dest)
            _log.append({
                "cfgp": configuration.get("metadata").get("name"),
                "features_labels": features_labels
            })
            if len(features_labels):
                api = self.get_api_client()
                for feature_lbl in features_labels:
                    prefix, name = feature_lbl.split("/")
                    selector = {
                        f"{prefix[len('features.'):]}/provides-feature": name,
                    }
                    _log.append({
                        "selector": selector
                    })
                    cfgps = ConfigurationProvider.objects(api).filter(
                        namespace=dest.get("metadata").get("namespace"),
                        selector=selector
                    )
                    for cfgp in cfgps:
                        _log.append({
                            "found": cfgp.name
                        })
                        appliesTo = cfgp.obj.get("spec").get("appliesTo")
                        if check_applies_to(appliesTo, labels):
                            apply_configuration(cfgp.obj, dest=dest, root_expr=root_expr, preserve_name=preserve_name,
                                                _log=_log)

            apply_configuration(configuration=configuration, dest=dest,
                                root_expr=root_expr, preserve_name=preserve_name, _log=_log)

    def applies_to(self, appliesTo, labels):
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
        return match

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