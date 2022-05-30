#from k8s_functions import K8sObjectsQuery

from k8s_functions import K8sObjectsQuery, ConfigurationProvider
from krules_core import RuleConst as Const
from krules_core.base_functions import *

from features import update_features_labels
from cfgp import apply_configuration, check_applies_to

rulename = Const.RULENAME
subscribe_to = Const.SUBSCRIBE_TO
ruledata = Const.RULEDATA
filters = Const.FILTERS
processing = Const.PROCESSING


class ApplyConfiguration(K8sObjectsQuery):

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
            apiversion="krules.dev/v1alpha1", kind="ConfigurationProvider",
            namespace=self.payload["request"]["namespace"],
            foreach=lambda obj: self._update_configuration_if_match(
                configuration=obj.obj,
                dest=self.payload["__mutated_object"],
                root_expr=root_expr,
                preserve_name=preserve_name,
                _log=self.payload["_log"]
            )
        )


class CheckTarget(RuleFunctionBase):

    def execute(self):

        dst = self.payload["__mutated_object"]
        target = dst["spec"].get("target", dst["metadata"].get("name"))
        if "_log_checktarget" not in self.payload:
            self.payload["_log_checktarget"] = []
        _logs = self.payload["_log_checktarget"]
        if target is not None:
            _logs.append(f"target is not None: {target}")
            try:
                app_label, name = target.split(":")
                _logs.append(f"split: {app_label}, {name}")
            except ValueError:
                _logs.append("ValueError")
                name = target
                app_label = "krules.dev/app"
            _logs.append(f"set: {app_label}, {name}")
            dst["spec"]["target"] = ":".join([app_label, name])

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
    """
    Check and update serviceconfigurationproviders target/.metadata.name 
    """,
    {
        rulename: "check-scfgp-target",
        subscribe_to: [
            "mutate-serviceconfigurationprovider-create",
            "mutate-serviceconfigurationprovider-update",
        ],
        ruledata: {
            processing: [
                CheckTarget()
            ]
        }
    },
]