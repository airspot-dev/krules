import json

from k8s_functions import *
from krules_core import RuleConst as Const

rulename = Const.RULENAME
subscribe_to = Const.SUBSCRIBE_TO
ruledata = Const.RULEDATA
filters = Const.FILTERS
processing = Const.PROCESSING


def _scfgp_to_cfgp(scfgp_obj):
    prefix, target = scfgp_obj['spec']['target'].split(":")
    key = f"services.{target}"
    appliesTo = {
        prefix: target
    }
    spec_from = scfgp_obj["spec"]
    cfgp_obj = {
        "apiVersion": "krules.dev/v1alpha1",
        "kind": "ConfigurationProvider",
        "metadata": {
            "namespace": scfgp_obj["metadata"]["namespace"],
            "name": scfgp_obj["metadata"]["name"],
            "labels": {
                "config.krules.dev/provider": scfgp_obj["metadata"]["name"],
                "config.krules.dev/provider_type": "service"
            },
            "annotations": {
                "krules.dev/features": json.dumps(spec_from.get("features", {}))
            }
        },
        "spec": {
            "key": key,
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
        rulename: "on-cfgp-to-scfgp-create",
        subscribe_to: "validate-serviceconfigurationprovider-create",
        ruledata: {
            processing: [
                K8sObjectCreate(
                    lambda payload: _scfgp_to_cfgp(payload["request"]["object"])
                )
            ]
        }
    },
    {
        rulename: "on-cfgp-to-scfgp-update",
        subscribe_to: "validate-serviceconfigurationprovider-update",
        ruledata: {
            processing: [
                K8sObjectUpdate(
                    lambda payload: _scfgp_to_cfgp(payload["request"]["object"]),
                    name=lambda payload: payload["request"]["name"],
                    apiversion="krules.dev/v1alpha1",
                    kind="ConfigurationProvider",
                    namespace=lambda payload: payload["request"]["namespace"]
                )
            ]
        }
    },
    {
        rulename: "scfgp-on-delete-clean-cfgps",
        subscribe_to: "validate-serviceconfigurationprovider-delete",
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