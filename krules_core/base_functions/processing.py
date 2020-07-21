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
from collections.abc import Mapping

from krules_core.route.router import DispatchPolicyConst

from krules_core.base_functions import RuleFunctionBase


## PAYLOAD FUNCTIONS ##############################################################

class UpdatePayload(RuleFunctionBase):
    """
    Update the payload _merging_ the received arguments interpreted as a dictionary
    """

    @staticmethod
    def _update(d, u):
        for k, v in u.items():
            if isinstance(v, Mapping):
                d[k] = UpdatePayload._update(d.get(k, {}), v)
            elif isinstance(v, list):
                v.extend(d.get(k, []))
                d[k] = v
            else:
                d[k] = v
        return d

    def execute(self, merge_dict):
        """
        Args:
            merge_dict: Dictionary to merge with
        """
        self._update(self.payload, merge_dict)


class SetPayloadProperties(RuleFunctionBase):
    """
    Set any number of properties in the payload. Existing properties are overridden
    """

    def execute(self, **kwargs):
        """
        Args:
              **kwargs: Each named paramenter is the key and the value to update with. The value can be a callable
                and it receives _eventually_ the previous value for that key. This means that the callable should be declared
                with a variable length number of arguments (*args)
        """
        for k, v in kwargs.items():
            if inspect.isfunction(v):
                args = []
                if k in self.payload:
                    args.append(self.payload[k])
                v = v(*args)
            self.payload[k] = v


class SetPayloadProperty(SetPayloadProperties):
    """
    Set a single property
    """

    def execute(self, property_name, value):
        """
        Args:
            property_name: A key in the dictionary,
            value: Value to set. Can be a callable (see SetPayloadProperties)
        """
        super().execute(**{property_name: value})


## SUBJECT FUNCTIONS ################################################################


class SetSubjectProperty(RuleFunctionBase):
    """
    Set a single property of the subject
    """
    def execute(self, property_name, value, extended=False, muted=False, cached=True):
        """
        Args:
            property_name: Name of the property to set. It may or may not exist
            value: Value to set. It can be a callable and receives (optionally) the current property value.
               If the property does not exist yet, it receives None
               (it is not possible to discriminate from an existing variable with the value None)
        """
        if extended:
            fn = lambda v: self.subject.set_ext(property_name, v, cached)
        else:
            fn = lambda v: self.subject.set(property_name, v, muted, cached)

        return fn(value)


class SetSubjectPropertySilently(SetSubjectProperty):
    """
    Set a property silently (no property changed event)
    """
    def execute(self, property_name, value, extended=False, cached=True, **kwargs):
        return super().execute(property_name, value, extended=extended, muted=True, cached=cached)


class StoreSubjectProperty(SetSubjectProperty):
    """
    Set a property directly to the storage without using the cache
    """
    def execute(self, property_name, value, extended=False, muted=False, **kwargs):
        return super().execute(property_name, value, extended=extended, muted=muted, cached=False)


class StoreSubjectPropertySilently(SetSubjectProperty):
    """
    Set a property directly to the storage without using the cache and without emit property changed events
    """
    def execute(self, property_name, value, extended=False, **kwargs):
        return super().execute(property_name, value, extended=extended, muted=True, cached=False)


class SetSubjectExtendedProperty(SetSubjectProperty):
    """
    Set an extended property of the subject
    """
    def execute(self, property_name, value, cached=True, **kwargs):
        return super().execute(property_name, value, extended=True, muted=True, cached=cached)


class SetSubjectProperties(RuleFunctionBase):
    """
        Set multiple properties in subject from dictionary. This is allowed only by using cache
        and not for extended properties
        Selectively emit property changed events
    """

    def execute(self, props, unmuted=[]):
        """
        Args:
            props: The properties to set
            unmuted: List of property names for which emit property changed events
        """
        for name, value in props.items():
            self.subject.set(name, value, muted=name not in unmuted)


class IncrementSubjectProperty(RuleFunctionBase):
    """
    Increment a numeric property in the subject. This is a conveniencs functions
    useful to accessing counters in a concurrent system. Implicitly
    call directly the storage backend bypassing the cache
    """
    def execute(self, property_name, amount=1, muted=False):
        if not isinstance(amount, (int, float, complex)):
            raise TypeError("amount must be a numeric type")
        return self.subject.set(
            property_name, lambda x: x is None and 0 + amount or x + amount, muted, cached=False)


class IncrementSubjectPropertySilently(IncrementSubjectProperty):

    def execute(self, property_name, amount=1, **kwargs):
        super().execute(property_name, amount, True)


class DecrementSubjectProperty(RuleFunctionBase):
    """
    Increment a numeric property in the subject. This is a conveniencs functions
    useful to accessing counters in a concurrent system. Implicitly
    call directly the storage backend bypassing the cache
    """
    def execute(self, property_name, amount=1, is_mute=False):
        if not isinstance(amount, (int, float, complex)):
            raise TypeError("amount must be a numeric type")

        return self.subject.set(
            property_name, lambda x: x is None and 0 - amount or x - amount, is_mute, cached=False)


class DecrementSubjectPropertySilently(DecrementSubjectProperty):

    def execute(self, property_name, amount=1, **kwargs):
        return super().execute(property_name, amount, True)


class StoreSubject(RuleFunctionBase):
    """
    Flush the cache
    """

    def execute(self):
        self.subject.store()


class FlushSubject(RuleFunctionBase):
    """
    Remove this subject and all of his properties
    """

    def execute(self):
        self.subject.flush()


#####################################################################################


class Route(RuleFunctionBase):
    """
    Produce an event inside and/or outside the ruleset according to _dispatch_policy_
    For "sending outside" the event we mean to deliver it to the dispatcher component
    """

    def execute(self, type=None, subject=None, payload=None, dispatch_policy=DispatchPolicyConst.DEFAULT):
        """
        Args:
            type: The event type. Default is current processing event type
            subject: New subject or the current subject as default
            payload: The payload of the event or the current payload
            dispatch_policy: Router -> dispatcher policy. Available choices are defined in
                 krules_core.route.router.DispatchPolicyConst as:

                    DEFAULT: Dispatched outside only when no handler is found in current ruleset
                    ALWAYS: Always dispatched even if an handler is found and processed in the current ruleset
                    NEVER: Never dispatched outside
                    DIRECT: Skip to search for a local handler and send outside directly
        """

        from krules_core.providers import event_router_factory
        if type is None:
            type = self.type
        if subject is None:
            subject = self.subject
        if payload is None:
            payload = self.payload

        event_router_factory().route(type, subject, payload, dispatch_policy=dispatch_policy)




class RaiseException(RuleFunctionBase):
    """
    Raise an exception
    """

    def execute(self, ex):

        raise ex

