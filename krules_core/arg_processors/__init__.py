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
        """
        return: True if arg must be processed by this class False if not.
        """
        raise NotImplementedError()

    def process(self, instance):
        """
        return: Processed argument.
        """
        raise NotImplementedError()


class DefaultArgProcessor(BaseArgProcessor):

    @staticmethod
    def interested_in(arg):
        return True

    def process(self, instance):
        return self._arg


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


class CallableWithSelfArgProcessor(BaseArgProcessor):

    @staticmethod
    def interested_in(arg):
        try:
            sig = inspect.signature(arg)
            return len(sig.parameters) == 1 and "self" in sig.parameters
        except TypeError:
            return False

    def process(self, instance):
        return self._arg(instance)


processors.append(CallableWithSelfArgProcessor)


class CallableWithPayloadArgProcessor(BaseArgProcessor):

    @staticmethod
    def interested_in(arg):
        try:
            sig = inspect.signature(arg)
            return len(sig.parameters) == 1 and "payload" in sig.parameters
        except TypeError:
            return False

    def process(self, instance):
        return self._arg(instance.payload)


processors.append(CallableWithPayloadArgProcessor)


class CallableWithSubjectArgProcessor(BaseArgProcessor):

    @staticmethod
    def interested_in(arg):
        try:
            sig = inspect.signature(arg)
            return len(sig.parameters) == 1 and "subject" in sig.parameters
        except TypeError:
            return False

    def process(self, instance):
        return self._arg(instance.subject)


processors.append(CallableWithSubjectArgProcessor)


