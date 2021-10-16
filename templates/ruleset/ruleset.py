import os
from krules_core import RuleConst as Const
from krules_core.base_functions import *

ruleset_config = configs_factory()["services"][os.environ["CE_SOURCE"]]

rulename = Const.RULENAME
subscribe_to = Const.SUBSCRIBE_TO
ruledata = Const.RULEDATA
filters = Const.FILTERS
processing = Const.PROCESSING

rulesdata = []
