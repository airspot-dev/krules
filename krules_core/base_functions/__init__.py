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
from krules_core.arg_processors import processors, DefaultArgProcessor
from krules_core.providers import event_router_factory, configs_factory


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
    event_type = ""
    router = object()
    configs = {}
    rule_name = ""

    def __init__(self, *args, **kwargs):
        self._args = []
        for a in args:
            self._args.append(self._get_arg_processor(a))

        self._kwargs = {}
        for k, v in kwargs.items():
            self._kwargs[k] = self._get_arg_processor(v)


    @staticmethod
    def _get_arg_processor(arg):
        for processor in processors:
            if processor.interested_in(arg):
                return processor(arg)
        return DefaultArgProcessor(arg)

    def _get_args(self, instance):
        args = []
        for processor in self._args:
            args.append(processor.process(instance))
        return tuple(args)

    def _get_kwargs(self, instance):
        kwargs = {}
        for key, processor in self._kwargs.items():
            kwargs[key] = processor.process(instance)
        return kwargs

    @abstractmethod
    def execute(self, *args, **kwargs):
        raise NotImplementedError("execute")


from krules_core.base_functions.filters import *
from krules_core.base_functions.processing import *
from krules_core.base_functions.misc import *


def Callable(_callable):
    return type("_CallableRuleFunction", (RuleFunctionBase,), {"execute": _callable})
