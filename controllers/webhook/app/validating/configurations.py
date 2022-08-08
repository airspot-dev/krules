import os
import re

from krules_core import RuleConst as Const
from krules_core.base_functions import *

from . import Deny

rulename = Const.RULENAME
subscribe_to = Const.SUBSCRIBE_TO
ruledata = Const.RULEDATA
filters = Const.FILTERS
processing = Const.PROCESSING

SYS_SVC_REGEX = re.compile("^system:[^:]+$")

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
                                    payload["request"]["oldObject"].get("metadata", {}).get("labels", [])
                ),
                Filter(
                    lambda payload:
                    payload["request"]["userInfo"]["username"] !=
                        "system:serviceaccount:{0}:{0}".format(
                            os.environ["SVC_ACC_NAME"]
                        ) and not SYS_SVC_REGEX.match(payload["request"]["userInfo"]["username"])
                ),
            ],
            processing: [
                Deny(lambda payload: f"owned by configuration provider (using: {payload['request']['userInfo']['username']}")
            ]
        }
    }
]