import os
from krules_core import RuleConst as Const
from krules_core.base_functions import *
from krules_core.event_types import *


ruleset_config: dict = configs_factory()["rulesets"][os.environ["CE_SOURCE"]]

rulesdata = []
