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
import socket

from krules_core import RuleConst
import os

from krules_core.models import Rule


def load_rules_from_rulesdata(rulesdata):

    from krules_core.core import RuleFactory

    description = ""
    for el in rulesdata:
        if isinstance(el, str):
            description = el
        elif isinstance(el, Rule) or isinstance(el, dict):
            if isinstance(el, Rule):
                el = el.dict()
            if len(description):
                el[RuleConst.DESCRIPTION] = description
            if el.get(RuleConst.SUBSCRIBE_TO, None) is None:
                el[RuleConst.SUBSCRIBE_TO] = "*"
            RuleFactory.create(**el)
            description = ""


def get_source():
    source = os.environ.get("CE_SOURCE")
    if source is None:
        if "K_SERVICE" in os.environ:
            source = os.environ["K_SERVICE"]
        else:
            source = socket.gethostname()
    return source
