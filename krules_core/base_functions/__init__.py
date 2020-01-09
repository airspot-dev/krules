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



from abc import ABCMeta, abstractmethod
#import jsonpath_rw_ext as jp
from krules_core.subject.tests.mocksubject import MockSubject


class with_payload(object):

    def __init__(self, func):
        self.func = func

    def __call__(self, payload):
        self._result = self.func(payload)
        return self._result

    def __repr__(self):
        if not hasattr(self, "_result"):
            return "[not called]"
        return str(self._result)

    def result(self):
        return getattr(self, "_result", None)

# TODO: with_payload_jp

# TODO: need testing
class with_subject(object):

    def __init__(self, func):
        self.func = func

    def __call__(self, subject):
        self._result = self.func(subject)
        return self._result

    def __repr__(self):
        if not hasattr(self, "_result"):
            return "[not called]"
        return str(self._result)

    def result(self):
        return getattr(self, "_result", None)

# TODO: with_subject_jp

# TODO: test
class with_self(object):

    def __init__(self, func):
        self.func = func

    def __call__(self, _class):
        self._result = self.func(_class)
        return self._result

    def __repr__(self):
        if not hasattr(self, "_result"):
            return "[not called]"
        return str(self._result)

    def result(self):
        return getattr(self, "_result", None)


class RuleFunctionBase:

    __metaclass__ = ABCMeta

    # just for the ide happiness
    subject = MockSubject("mock")
    payload = {}
    message = ""

    def __init__(self, *args, **kwargs) :
        self._args = args
        self._kwargs = kwargs

    def _get_args(self, _cinst):
        for _a in self._args:
            if isinstance(_a, with_self):
                yield _a(_cinst)
            elif isinstance(_a, with_payload):
                yield _a(_cinst.payload)
            elif isinstance(_a, with_subject):
                yield _a(_cinst.subject)
            elif isinstance(_a, (list, tuple, dict)):
                yield self._parse_params(_a, _cinst.payload)
            else:
                yield _a

    def _get_kwargs(self, _cinst):
        _kwargs = self._kwargs.copy()
        return self._parse_params(_kwargs, _cinst)

    def _parse_params(self, params, _cinst):
        for k in params:
            if isinstance(params, dict):
                index = k
            else:
                index = params.index(k)
            if isinstance(params[index], with_payload):
                params[index] = params[index](_cinst.payload)
            if isinstance(params[index], with_subject):
                params[index] = params[index](_cinst.subject)
            if isinstance(params[index], with_self):
                params[index] = params[index](_cinst)
            elif isinstance(params[index], (list, tuple, dict)):
                params[index] = self._parse_params(params[index], _cinst.payload)
        return params

    @abstractmethod
    def execute(self, *args, **kwargs):
        raise NotImplementedError("execute")


from .filters import *
from .processing import *

