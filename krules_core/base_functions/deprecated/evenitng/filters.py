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


class IsInternalEvent(RuleFunctionBase):

    def execute(self):

        _event_info = self.payload.get("_event_info", {})

        if "message_source" in _event_info:
            return False

        return True
