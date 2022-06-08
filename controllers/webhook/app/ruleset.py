import copy
#import re
from krules_core import RuleConst as Const
from krules_core.base_functions import Process, Filter

from mutating.configurations import rulesdata as mutating_configurations_rulesdata
from mutating.podenv import rulesdata as mutating_podenv_rulesdata
from mutating.initalization import rulesdata as initalization_rulesdata
from validating.podenv import rulesdata as validating_podenv_rulesdata
from validating.configurations import rulesdata as validating_configurations_rulesdata
from validating.sendout import rulesdata as validating_sendout_rulesdata
from mutating import MakePatch

from flask import g

rulename = Const.RULENAME
subscribe_to = Const.SUBSCRIBE_TO
ruledata = Const.RULEDATA
filters = Const.FILTERS
processing = Const.PROCESSING

#REGEX_MUTATING_EVENT=re.compile("mutate-[a-z]+-(create|update)")

MUTATION_EVENT_TYPES = []

for el in ["pod", "deployment", "kservice", "serviceconfigurationprovider", "featureconfigurationprovider"]:
    MUTATION_EVENT_TYPES.extend((
        f"mutate-{el}-create",
        f"mutate-{el}-update",
    ))

rulesdata = [
    """
    Copy source in destination
    """,
    {
        rulename: "mutate-prepare-dest-object",
        subscribe_to: MUTATION_EVENT_TYPES,
        ruledata: {
            filters: [
                Filter(
                    #lambda self: REGEX_MUTATING_EVENT.match(self.event_type) is not None
                    lambda: g.step == "MUTATE"
                )
            ],
            processing: [
                Process(
                    lambda payload: payload.setdefault(
                        "__mutated_object",
                        copy.deepcopy(payload["request"]["object"])
                    )
                )
            ]
        }
    },
  ] \
  + initalization_rulesdata \
  + mutating_podenv_rulesdata \
  + mutating_configurations_rulesdata \
  + validating_podenv_rulesdata \
  + validating_configurations_rulesdata \
  + validating_sendout_rulesdata \
  + [
    """
    Make patch
    """,
    {
        rulename: "mutate-make-patches",
        subscribe_to: MUTATION_EVENT_TYPES,
        ruledata: {
            filters: [
                Filter(
                    #lambda self: REGEX_MUTATING_EVENT.match(self.event_type)
                    lambda: g.step == "MUTATE"
                )
            ],
            processing: [
                MakePatch(
                    src=lambda payload: payload["request"]["object"],
                    dst=lambda payload: payload["__mutated_object"],
                )
            ]
        }
    },
    # {
    #     rulename: "do-absolutely-nothing",
    #     subscribe_to: ["*"],
    #     ruledata: {
    #         processing: [
    #             Process(
    #                 lambda: None
    #             )
    #         ]
    #     }
    # }
]
