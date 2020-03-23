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



from krules_core.route.router import DispatchPolicyConst
from krules_core.base_functions import RuleFunctionBase


class PyCall(RuleFunctionBase):
    """
    Call a python function
    """

    def execute(self, _call, *args, **kwargs):
        payload_dest = kwargs.pop("payload_dest", "pycall_returns")
        self.payload[payload_dest] = _call(*args, **kwargs)


class ReturnBoolean(RuleFunctionBase):
    """
    Just return provided parameter as booleand
    It can be useful to enable/disable manuallyV
    the execution of a rule
    """

    def execute(self, value):

        return bool(value)


class SetPayloadProperty(RuleFunctionBase):
    """
    Set property in payload, if value is not provided set as None
    """

    def execute(self, name, value=None):

        if hasattr(value, 'copy'):
            value = value.copy()

        self.payload[name] = value
        return True


class SetSubjectProperty(RuleFunctionBase):
    """
    Set property in subject. In value is not provided set as None
    """

    def execute(self, name, value=None):

        setattr(self.subject, name, value)
        return True

class SetSubjectProperties(RuleFunctionBase):
    """
    Set multiple properties in subject from dictionary
    """

    def execute(self, props):

        # TODO: important! use single redis operation

        for name, value in props.items():
            setattr(self.subject, name, value)
        return True

class SetSubjectExtendedProperty(RuleFunctionBase):
    """
    Set extended property
    Each subject has a set of extended properties. They can only be of string type and are not reactive.
    The use of this kind of property is open,
    for example it can be used to define specific routing rules for different classes of subjects
    in the dispatcher implementation
    """

    def execute(self, name, value):
        self.subject.set_ext(name, value)


class SetSubjectPropertyDefault(RuleFunctionBase):
    """
    if the property does not yet exist it sets the default value
    """

    def execute(self, name, value):
        """
        :param name: Name of the property
        :param value: Set this value if the property does not exist
        """

        try:
            getattr(self.subject, name)
        except AttributeError:
            setattr(self.subject, name, value)

        return True  # can be used in filters


class IncrSubjectProperty(RuleFunctionBase):
    """
    Increment subject property
    """

    def execute(self, name, value=1):

        try:
            prop = getattr(self.subject, name)
            prop.incr(value)
        except AttributeError:
            setattr(self.subject, name, 0)
            prop.incr(value)


class DecrSubjectProperty(RuleFunctionBase):
    """
    Decrement subject property
    """

    def execute(self, name, value=1):
        try:
            prop = getattr(self.subject, name)
            prop.decr(value)
        except AttributeError:
            setattr(self.subject, name, 0)
            prop.decr(value)


class FlushSubject(RuleFunctionBase):

    def execute(self):

        self.subject.flush()


class Route(RuleFunctionBase):

    def execute(self, message=None, subject=None, payload=None, dispatch_policy=DispatchPolicyConst.DEFAULT):
        """
        Route message
        :param message:
        :param subject:
        :param payload:
        :return:
        """
        from krules_core.providers import message_router_factory
        if message is None:
            message = self.message
        if subject is None:
            subject = self.subject
        if payload is None:
            payload = self.payload

        if "_event_info" in self.payload:
            payload["_event_info"] = self.payload["_event_info"]


        message_router_factory().route(message, subject, payload, dispatch_policy=dispatch_policy)




class RaiseException(RuleFunctionBase):
    """
    Raise an exception
    """

    def execute(self, ex):
        """

        :param class_: Exception class (default: Exception)
        :param args: Exception args
        :param kwargs: Exception kwargs
        :return:
        """
        raise ex


# TODO: unit tests
class MapList(RuleFunctionBase):

    def execute(self, _list, func, payload_dest=None, subject_dest=None):

        # TODO: workaround when used with with_subject or with_payload
        try:
            iter(_list)
        except TypeError:
            _list = _list.result()

        ll = list(map(func, _list))

        if payload_dest:
            self.payload[payload_dest] = ll

        if subject_dest:
            setattr(self.subject, subject_dest, ll)


