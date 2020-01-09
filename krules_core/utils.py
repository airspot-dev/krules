# Copyright 2019 The KRules Authors
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


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
