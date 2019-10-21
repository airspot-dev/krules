from krules_core import RuleConst
from krules_core.core import RuleFactory
import os

def load_rules_from_rulesdata(rulesdata):

    description=""
    for el in rulesdata:
        if type(el) == type(""):
            description=el
        elif type(el) == type({}) and RuleConst.RULENAME in el:
            el[RuleConst.DESCRIPTION] = description
            if el.get(RuleConst.SUBSCRIBE_TO, None) is None:
                el[RuleConst.SUBSCRIBE_TO] = os.environ["TOPIC"]  # TODO: should not rely on this variable. The name of the subscription message should be inferred differently
            RuleFactory.create(**el)
            description = ""
