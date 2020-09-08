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

processors = []


class BaseArgProcessor:

    def __init__(self, arg):
        self._arg = arg

    @staticmethod
    def interested_in(arg):
        return False

    def process(self, instance):
        return self._arg(instance)


class NotCallableArgProcessor(BaseArgProcessor):

    @staticmethod
    def interested_in(arg):
        return not hasattr(arg, '__call__')

    def process(self, instance):
        return self._arg


processors.append(NotCallableArgProcessor)


class MultiParamsCallableArgProcessor(BaseArgProcessor):

    @staticmethod
    def interested_in(arg):
        try:
            sig = inspect.signature(arg)
            return len(sig.parameters) > 1
        except TypeError:
            return False

    def process(self, instance):
        return self._arg


processors.append(MultiParamsCallableArgProcessor)


class SimpleCallableArgProcessor(BaseArgProcessor):

    @staticmethod
    def interested_in(arg):
        try:
            sig = inspect.signature(arg)
            return len(sig.parameters) == 0
        except TypeError:
            return False

    def process(self, _):
        return self._arg()


processors.append(SimpleCallableArgProcessor)


class CallableWithSelf(BaseArgProcessor):

    @staticmethod
    def interested_in(arg):
        try:
            sig = inspect.signature(arg)
            return len(sig.parameters) == 1 and "self" in sig.parameters
        except TypeError:
            return False

    def process(self, instance):
        return self._arg(instance)


processors.append(CallableWithSelf)


class CallableWithPayload(BaseArgProcessor):

    @staticmethod
    def interested_in(arg):
        try:
            sig = inspect.signature(arg)
            return len(sig.parameters) == 1 and "payload" in sig.parameters
        except TypeError:
            return False

    def process(self, instance):
        return self._arg(instance.payload)


processors.append(CallableWithPayload)


class CallableWithSubject(BaseArgProcessor):

    @staticmethod
    def interested_in(arg):
        try:
            sig = inspect.signature(arg)
            return len(sig.parameters) == 1 and "subject" in sig.parameters
        except TypeError:
            return False

    def process(self, instance):
        return self._arg(instance.subject)


processors.append(CallableWithSubject)


