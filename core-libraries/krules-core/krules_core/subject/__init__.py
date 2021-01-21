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
import inspect
import json

class PayloadConst(object):

    PROPERTY_NAME = "property_name"
    VALUE = "value"
    OLD_VALUE = "old_value"


class PropertyType(object):

    DEFAULT = 'p'
    EXTENDED = 'e'


class _JsonProperty(object):

    def __init__(self, name, value=None):
        self.name = name
        self.value = value

    def json_value(self, *args, **kwargs):

        if inspect.isfunction(self.value):
            if len(inspect.signature(self.value).parameters) == 0:
                self._computed = self.value()
            else:
                self._computed = self.value(*args, **kwargs)
            return json.dumps(self._computed)
        return json.dumps(self.value)

    def get_value(self, *args, **kwargs):
        if hasattr(self, '_computed'):
            return self._computed
        if inspect.isfunction(self.value):
            if len(inspect.signature(self.value).parameters) == 0:
                return self.value()
            else:
                return self.value(*args, **kwargs)
        return self.value


class SubjectProperty(_JsonProperty):

    def __init__(self, name, value=None):
        super().__init__(name, value)
        self.type = PropertyType.DEFAULT


class SubjectExtProperty(_JsonProperty):

    def __init__(self, name, value=None):
        super().__init__(name, value)
        self.type = PropertyType.EXTENDED
