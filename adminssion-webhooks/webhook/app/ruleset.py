from krules_core.base_functions import *
from krules_core.providers import subject_factory

from ksvc.mutating import rulesdata as ksvc_mutating_rulesdata
from ksvc.validating import rulesdata as ksvc_validating_rulesdata

from krules_core import RuleConst as Const

rulename = Const.RULENAME
subscribe_to = Const.SUBSCRIBE_TO
ruledata = Const.RULEDATA
filters = Const.FILTERS
processing = Const.PROCESSING

rulesdata = [
    {
        rulename: "test-admission",
        subscribe_to: [
            "validating-request",
            "mutating-request",
        ],
        ruledata: {
            processing: [
                Route(
                    event_type="the-world-is-breaking-down",
                    subject=subject_factory("people", event_info={}),
                    payload={}
                ),
                RaiseException(Exception("hello"))
            ]
        }
    }

]

rulesdata = rulesdata + ksvc_mutating_rulesdata + ksvc_validating_rulesdata