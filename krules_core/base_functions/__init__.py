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
from krules_core.arg_processors import processors


# class with_payload(object):
#
#     def __init__(self, func):
#         self.func = func
#
#     def __call__(self, payload):
#         self._result = self.func(payload)
#         return self._result
#
#     def __repr__(self):
#         if not hasattr(self, "_result"):
#             return "[not called]"
#         return str(self._result)
#
#     def result(self):
#         return getattr(self, "_result", None)
#
# # TODO: with_payload_jp
#
# # TODO: need testing
# class with_subject(object):
#
#     def __init__(self, func):
#         self.func = func
#
#     def __call__(self, subject):
#         self._result = self.func(subject)
#         return self._result
#
#     def __repr__(self):
#         if not hasattr(self, "_result"):
#             return "[not called]"
#         return str(self._result)
#
#     def result(self):
#         return getattr(self, "_result", None)
#
# # TODO: with_subject_jp
#
# # TODO: test
# class with_self(object):
#
#     def __init__(self, func):
#         self.func = func
#
#     def __call__(self, _class):
#         self._result = self.func(_class)
#         return self._result
#
#     def __repr__(self):
#         if not hasattr(self, "_result"):
#             return "[not called]"
#         return str(self._result)
#
#     def result(self):
#         return getattr(self, "_result", None)


class RuleFunctionBase:

    __metaclass__ = ABCMeta

    subject = object()  # just for the ide happiness

    payload = {}
    type = ""

    def __init__(self, *args, **kwargs):
        self._args = args
        self._kwargs = kwargs

    def _get_args(self, instance):

        args = list(self._args)
        for i in range(len(self._args)):
            v = self._args[i]
            for processor in processors:
                if processor.interested_in(v):
                #if processor.interested_in(self._args[i]):
                    args[i] = processor.process(instance, v)
                    #self._args[i] = processor.process(instance, v)
                    break
                else:
                    pass
        return args

    def _get_kwargs(self, instance):

        kwargs = self._kwargs.copy()
        for key in kwargs:
            for processor in processors:
                if processor.interested_in(kwargs[key]):
                #if processor.interested_in(self._kwargs[key]):
                    kwargs[key] = processor.process(instance, kwargs[key])
                    break
                else:
                    pass
        return kwargs


    @abstractmethod
    def execute(self, *args, **kwargs):
        raise NotImplementedError("execute")


from krules_core.base_functions.filters import *
from krules_core.base_functions.processing import *


def Callable(_callable):
    return type("_CallableRuleFunction", (RuleFunctionBase,), {"execute": _callable})
