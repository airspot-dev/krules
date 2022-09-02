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
from pydantic.fields import ModelField

from krules_core.arg_processors import processors, DefaultArgProcessor, BaseArgProcessor
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

    # we want to get invocation parameters
    # of the final class not the base
    def __new__(cls, *args, **kwargs):
        obj = super().__new__(cls)
        setattr(obj, "_copy_args", args)
        setattr(obj, "_copy_kwargs", kwargs)
        processor_args = []
        for a in args:
            processor_args.append(obj._get_arg_processor(a))

        processor_kwargs = {}
        for k, v in kwargs.items():
            processor_kwargs[k] = obj._get_arg_processor(v)
        setattr(obj, "_processor_args", processor_args)
        setattr(obj, "_processor_kwargs", processor_kwargs)
        return obj

    @staticmethod
    def _get_arg_processor(arg):
        for processor in processors:
            if processor.interested_in(arg):
                if isinstance(arg, BaseArgProcessor):
                    return arg
                return processor(arg)
        return DefaultArgProcessor(arg)

    def _get_processed_args(self, instance):
        args = []
        for processor in self._processor_args:
            args.append(processor.process(instance, processor._arg))
        return tuple(args)

    def _get_processed_kwargs(self, instance):
        kwargs = {}
        for key, processor in self._processor_kwargs.items():
            kwargs[key] = processor.process(instance, processor._arg)
        return kwargs

    # @abstractmethod
    # def execute(self, *args, **kwargs):
    #     raise NotImplementedError("execute")


from krules_core.base_functions.filters import *
from krules_core.base_functions.processing import *
from krules_core.base_functions.misc import *


def Callable(_callable):
    return type("_CallableRuleFunction", (RuleFunctionBase,), {"execute": _callable})
