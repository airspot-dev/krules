import json

from k8s_functions import *
from krules_core import RuleConst as Const

rulename = Const.RULENAME
subscribe_to = Const.SUBSCRIBE_TO
ruledata = Const.RULEDATA
filters = Const.FILTERS
processing = Const.PROCESSING


def _fcfgp_to_cfgp(fcfgp_obj):
    key = f"features.krules.dev/{fcfgp_obj['metadata']['name']}"
    appliesTo = {
        key: "enabled"
    }
    spec_from = fcfgp_obj["spec"]
    cfgp_obj = {
        "apiVersion": "krules.dev/v1alpha1",
        "kind": "ConfigurationProvider",
        "metadata": {
            "namespace": fcfgp_obj["metadata"]["namespace"],
            "name": fcfgp_obj["metadata"]["name"],
            "labels": {
                "config.krules.dev/provides-feature": fcfgp_obj["metadata"]["name"],
                "config.krules.dev/provider": fcfgp_obj["metadata"]["name"],
                "config.krules.dev/provider_type": "feature"
            }
        },
        "spec": {
            "key": key,
            "description": spec_from.get("description", ""),
            "appliesTo": appliesTo,
            "data": spec_from.get('data', {}),
            "container": spec_from.get('container', {}),
            "extraVolumes": spec_from.get('extraVolumes', []),
            "extensions": spec_from.get('extensions', {})
        }
    }
    return cfgp_obj


rulesdata = [
    {
        rulename: "on-cfgp-to-fcfgp-create",
        subscribe_to: "validate-featureconfigurationprovider-create",
        ruledata: {
            processing: [
                K8sObjectCreate(
                    lambda payload: _fcfgp_to_cfgp(payload["request"]["object"])
                )
            ]
        }
    },
    {
        rulename: "on-cfgp-to-fcfgp-update",
        subscribe_to: "validate-featureconfigurationprovider-update",
        ruledata: {
            processing: [
                K8sObjectUpdate(
                    lambda payload: _fcfgp_to_cfgp(payload["request"]["object"]),
                    name=lambda payload: payload["request"]["name"],
                    apiversion="krules.dev/v1alpha1",
                    kind="ConfigurationProvider",
                    namespace=lambda payload: payload["request"]["namespace"]
                )
            ]
        }
    },
    {
        rulename: "fcfgp-on-delete-clean-cfgps",
        subscribe_to: "validate-featureconfigurationprovider-delete",
        ruledata: {
            processing: [
                K8sObjectDelete(
                    name=lambda payload: payload["request"]["name"],
                    apiversion="krules.dev/v1alpha1",
                    kind="ConfigurationProvider",
                    namespace=lambda payload: payload["request"]["namespace"],
                )
            ]
        }
    },
]