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


from krules_core.base_functions import RuleFunctionBase


# TODO: test

class SetSubjectPropertyToPayload(RuleFunctionBase):
    """
    Dump a subject properties to the payload
    """

    def execute(self, name, payload_dest=None, fail_if_not_exists=False, default=None):


        res = default

        try:
            prop = getattr(self.subject, name)
            value = getattr(prop, '__wrapped__', prop)
            res = value
        except AttributeError:
            if fail_if_not_exists:
                return False
        if payload_dest is None:
            payload_dest = name
        self.payload[payload_dest] = res

        return True  # can be used in filters

