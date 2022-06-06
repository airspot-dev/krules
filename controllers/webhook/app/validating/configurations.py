import os

from krules_core import RuleConst as Const
from krules_core.base_functions import *

from . import Deny

rulename = Const.RULENAME
subscribe_to = Const.SUBSCRIBE_TO
ruledata = Const.RULEDATA
filters = Const.FILTERS
processing = Const.PROCESSING

rulesdata = [
    {
        rulename: "on-config-update-deny-if-owned",
        subscribe_to: [
            "validate-configmap-update",
            "validate-configmap-delete",
            "validate-configurationprovider-update",
            "validate-configurationprovider-delete",
        ],
        ruledata: {
            filters: [
                Filter(
                    lambda payload: "config.krules.dev/provider" in
                                    payload["request"]["oldObject"].get("metadata").get("labels")
                ),
                Filter(
                    lambda payload:
                    payload["request"]["userInfo"]["username"] != "system:serviceaccount:{0}:{0}".format(
                        os.environ["SVC_ACC_NAME"]
                    )
                ),
            ],
            processing: [
                Deny("owned by configuration provider")
            ]
        }
    }
]