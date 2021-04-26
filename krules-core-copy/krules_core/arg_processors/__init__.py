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
    """
    *Base Argument Processor class in which base methods are defined*
    """

    def __init__(self, arg):
        self._arg = arg

    @staticmethod
    def interested_in(arg):
        """
        Returns:
            True if arg must be processed by this class False if not.
        """

        raise NotImplementedError()

    def process(self, instance):
        """
        Returns:
            Processed argument.
        """

        raise NotImplementedError()


class DefaultArgProcessor(BaseArgProcessor):
    """
    *A simple Argument Processor which returns the argument itself.*
    """

    def __init__(self, arg):
        super().__init__(lambda: arg)

    @staticmethod
    def interested_in(arg):
        """
        Returns:
            Always True.
        """

        return True

    def process(self, instance):
        """
        Returns:
            Argument itself.
        """

        return self._arg()


class SimpleCallableArgProcessor(BaseArgProcessor):
    """
    *An Argument Processor specific for callable without parameters.*
    """

    @staticmethod
    def interested_in(arg):
        """
        Returns:
            True if the argument is a function which not expect any parameters.
        """

        try:
            sig = inspect.signature(arg)
            return len(sig.parameters) == 0
        except TypeError:
            return False

    def process(self, _):
        """
        Returns:
            Argument execution result.
        """

        return self._arg()


processors.append(SimpleCallableArgProcessor)


class CallableWithSelfArgProcessor(BaseArgProcessor):
    """
    *An Argument Processor specific for callable with *self* as unique parameter.*
    """

    @staticmethod
    def interested_in(arg):
        """
        Returns:
            True if the argument is a function which expect only self as unique argument.
        """

        try:
            sig = inspect.signature(arg)
            return len(sig.parameters) == 1 and "self" in sig.parameters
        except TypeError:
            return False

    def process(self, instance):
        """
        Returns:
            Argument execution result passing RuleFunction instance as argument.
        """

        return self._arg(instance)


processors.append(CallableWithSelfArgProcessor)


class CallableWithPayloadArgProcessor(BaseArgProcessor):
    """
    *An Argument Processor specific for callable with *payload* as unique parameter.*
    """

    @staticmethod
    def interested_in(arg):
        """
        Returns:
            True if the argument is a function which expect only *payload* as unique argument.
        """

        try:
            sig = inspect.signature(arg)
            return len(sig.parameters) == 1 and "payload" in sig.parameters
        except TypeError:
            return False

    def process(self, instance):
        """
        Returns:
            Return the argument execution result passing RuleFunction instance payload as argument.
        """

        return self._arg(instance.payload)


processors.append(CallableWithPayloadArgProcessor)


class CallableWithSubjectArgProcessor(BaseArgProcessor):
    """
    *An Argument Processor specific for callable with *subject* as unique parameter.*
    """

    @staticmethod
    def interested_in(arg):
        """
        Returns:
            True if the argument is a function which expect only *subject* as unique argument.
        """

        try:
            sig = inspect.signature(arg)
            return len(sig.parameters) == 1 and "subject" in sig.parameters
        except TypeError:
            return False

    def process(self, instance):
        """
        Returns:
            Return the argument execution result passing RuleFunction instance subject as argument.
        """

        return self._arg(instance.subject)


processors.append(CallableWithSubjectArgProcessor)
