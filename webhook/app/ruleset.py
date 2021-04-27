from krules_core import RuleConst as Const

from mutating.cfgp import rulesdata as mutating_configurations_rulesdata
from mutating.podenv import rulesdata as mutating_podenv_rulesdata
from validating.podenv import rulesdata as validating_podenv_rulesdata
from validating.cfgp import rulesdata as validating_cfgp_rulesdata

rulename = Const.RULENAME
subscribe_to = Const.SUBSCRIBE_TO
ruledata = Const.RULEDATA
filters = Const.FILTERS
processing = Const.PROCESSING


rulesdata = \
    mutating_podenv_rulesdata \
    + mutating_configurations_rulesdata \
    + validating_podenv_rulesdata \
    + validating_cfgp_rulesdata


