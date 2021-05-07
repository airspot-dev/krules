from krules_core import RuleConst as Const
from krules_core.base_functions import *

rulename = Const.RULENAME
subscribe_to = Const.SUBSCRIBE_TO
ruledata = Const.RULEDATA
filters = Const.FILTERS
processing = Const.PROCESSING

rulesdata = [
    """
    Send out the event when validation passes
    """,
    {
        rulename: "on-validated-sendout",
        subscribe_to: [
            "validate-configurationprovider-create",
            "validate-configurationprovider-update",
            "validate-configurationprovider-delete",
            "validate-namespace-create",
            "validate-namespace-update",
            "validate-broker-delete",
        ],
        ruledata: {
            filters: [
                Filter(
                    lambda payload: payload["response"]["allowed"] is True
                ),
                Filter(
                    lambda payload: payload["request"]["dryRun"] is False
                )
            ],
            processing: [
                Route(dispatch_policy=DispatchPolicyConst.DIRECT)
            ]
        }
    },
    """
    Send out the event for configmap deletion if referred to a cfgp
    """,
    {
        rulename: "on-cm-validated-sendout",
        subscribe_to: [
            "validate-configmap-delete",
        ],
        ruledata: {
            filters: [
                Filter(
                    lambda payload: payload["response"]["allowed"] is True
                ),
                Filter(
                    lambda payload: payload["request"]["dryRun"] is False
                ),
                Filter(
                    lambda payload:
                        "config.krules.airspot.dev/provider" in payload["request"]["oldObject"]["metadata"].get("labels", {})
                )
            ],
            processing: [
                Route(dispatch_policy=DispatchPolicyConst.DIRECT)
            ]
        }
    }

]