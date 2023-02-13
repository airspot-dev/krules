import os
from krules_core import RuleConst as Const
from krules_core.base_functions import *
from krules_core.event_types import *


rulename = Const.RULENAME
subscribe_to = Const.SUBSCRIBE_TO
ruledata = Const.RULEDATA
filters = Const.FILTERS
processing = Const.PROCESSING

ruleset_config: dict = configs_factory()["rulesets"][os.environ["CE_SOURCE"]]

rulesdata = []
