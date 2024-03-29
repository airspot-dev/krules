import copy

from krules_core import RuleConst as Const
from krules_core.base_functions import Process

from mutating.configurations import rulesdata as mutating_configurations_rulesdata
from mutating.podenv import rulesdata as mutating_podenv_rulesdata
from validating.podenv import rulesdata as validating_podenv_rulesdata
from validating.sendout import rulesdata as validating_sendout_rulesdata
from mutating import MakePatch

rulename = Const.RULENAME
subscribe_to = Const.SUBSCRIBE_TO
ruledata = Const.RULEDATA
filters = Const.FILTERS
processing = Const.PROCESSING

rulesdata = [
    """
    Ensure env element is present 
    """,
    {
        rulename: "mutate-prepare-dest-object",
        subscribe_to: [
            "mutate-pod-create",
            "mutate-pod-update",
            "mutate-deployment-create",
            "mutate-deployment-update",
            "mutate-kservice-create",
            "mutate-kservice-update",
        ],
        ruledata: {
            processing: [
                Process(
                    lambda payload: payload.setdefault(
                        "__mutated_object",
                        copy.deepcopy(payload["request"]["object"])
                    )
                )
            ]
        }
    }
] + \
    mutating_podenv_rulesdata \
    + mutating_configurations_rulesdata \
    + validating_podenv_rulesdata \
    + validating_sendout_rulesdata \
    + [
    """
    Ensure env element is present 
    """,
    {
        rulename: "mutate-make-patches",
        subscribe_to: [
            "mutate-pod-create",
            "mutate-pod-update",
            "mutate-deployment-create",
            "mutate-deployment-update",
            "mutate-kservice-create",
            "mutate-kservice-update",
        ],
        ruledata: {
            processing: [
                MakePatch(
                    src=lambda payload: payload["request"]["object"],
                    dst=lambda payload: payload["__mutated_object"],
                )
            ]
        }
    }
]
