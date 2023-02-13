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
from typing import Any, List

from krules_core.base_functions import RuleFunctionBase
from krules_core.providers import subject_factory
from krules_core.route.router import DispatchPolicyConst

from deepmerge import always_merger, Merger

from krules_core.subject.storaged_subject import Subject


class ProcessingFunction(RuleFunctionBase):
    __metaclass__ = ABCMeta

    @abstractmethod
    def execute(self, *args, **kwargs):
        raise NotImplementedError("execute")


class Process(ProcessingFunction):
    """
    *The best way to exploit it is to use it in combination with* `Argument Processors <https://intro.krules.io/ArgumentProcessors.html>`_.

    ::

        from krules_env import RULE_PROC_EVENT

        #...

        rulesdata = [
            {
                # Store processed events with Django ORM
                rulename: "processed-rules",
                subscibre_to: RULE_PROC_EVENT,
                ruledata: {
                    processing: [
                        Process(
                            lambda payload:(
                                ProcessedEvent.objects.create(
                                    rule_name=payload["name"],
                                    type=payload["type"],
                                    subject=payload["subject"],
                                    event_info=payload["event_info"],
                                    payload=payload["payload"],
                                    time=payload["event_info"].get("time", datetime.now().isoformat()),
                                    filters=payload["filters"],
                                    processing=payload["processing"],
                                    got_errors=payload["got_errors"],
                                    processed=payload["processed"],
                                    origin_id=payload["event_info"].get("originid", "-")
                                )
                            )
                        ),
                    ]
                }
            }
        ]

    """
    def execute(self, value: Any):
        """

        """
        pass


## PAYLOAD FUNCTIONS ##############################################################

class SetPayloadProperties(ProcessingFunction):
    """
    *Set the given properties in the payload, if some of that already exist will be overridden*

    ::

        rulesdata = [
            {
                rulename: "on-admin-login-update-payload",
                subscibre_to: "user-login",
                ruledata: {
                    filters: [
                        ...
                        # Check if user is admin
                    ]
                    processing: [
                        SetPayloadProperties(  # Definition with a dictionary
                            lambda: **{
                                "has_admin_access": True,
                                "last_login": datetime.now()
                            }
                        )
                    ]
                }
            },
            {
                rulename: "on-user-login-update-payload",
                subscibre_to: "user-login",
                ruledata: {
                    filters: [
                        ...
                        # Check if user has not admin privileges
                    ]
                    processing: [
                        SetPayloadProperties(  # Definition with named arguments
                            has_admin_access=False,
                            last_login=lambda:datetime.now()
                        )
                    ]
                }
            },
            # Thanks to ArgumentProcessor we can use a lambda, without that last_login
            # would be always equal to the Rule instantiation's datetime while we need the execution's one.
        ]
    """

    def execute(self, **kwargs):
        """
        Args:
              **kwargs: Each named paramenter is the key and the value to update with.
        """
        for k, v in kwargs.items():
            self.payload[k] = v


class SetPayloadProperty(SetPayloadProperties):
    """
    *Extends* `SetPayloadProperties <https://intro.krules.io/Processing.html#krules_core.base_functions.processing.SetPayloadProperties>`_
    *expecting a single property to set*

    ::

        rulesdata = [
            {
                rulename: "on-heather-onboarded-set-class",
                subscibre_to: "device-onboarded",
                ruledata: {
                    filters: [
                        ...
                        # Check if device has characteristics of an heather
                    ]
                    processing: [
                        SetPayloadProperty(
                            property_name="device_class",
                            value="heather"
                        )
                    ]
                }
            },
        ]
    """

    def execute(self, property_name: str, value: Any):
        """
        Args:
            property_name: Name of property which will be to set,
            value: Value to set.
        """
        super().execute(**{property_name: value})


class PayloadDeepMerge(ProcessingFunction):

    """
    Wraps: `Deepmerge library <https://deepmerge.readthedocs.io/en/latest/>`
    """

    def execute(self, data: dict, merger: Merger = always_merger):

        merger.merge(self.payload, data)

## SUBJECT FUNCTIONS ################################################################


class SetSubjectProperty(ProcessingFunction):
    """
    *Set a single property of the subject, supporting atomic operation.*
    *By default, the property is reactive unless is muted (muted=True) or extended (extended=True)*

    ::

        rulesdata = [
            {
                rulename: "set-device-class",
                subscibre_to: "device-onboarded",
                ruledata: {
                    filters: [
                        ...
                        # Check if device has characteristics of an heather
                    ]
                    processing: [
                        SetSubjectProperty(
                            property_name="device_class",
                            value="heather"
                        )
                    ]
                }
            },
            {
                rulename: "on-new-checkup-increment-counter",
                subscibre_to: "checkup",
                ruledata: {
                    processing: [
                        SetSubjectProperty(
                            property_name="checkup_cnt",
                            value=lambda x: x is None and 1 or x + 1 # Operation is atomic
                        )
                    ]
                }
            }
        ]
    """
    def execute(self,
                property_name: str, value: Any,
                extended: bool = False, muted: bool = False, use_cache: bool = True,
                subject: str | Subject = None,
                ):
        """
        Args:
            property_name: Name of the property to set. It may or may not exist
            value: Value to set. It can be a callable and receives (optionally) the current property value.
                If the property does not exist yet, it receives None. Note that value setting is an atomic operation.
            extended: If True set an extended property instead a standard one. [default False]
            muted: If True no subject-property-changed will be raised after property setting. Note that extended
                properties are always muted so, if extended is True, this parameter will be ignored. [default False]
            use_cache: If False store the property value immediately on the storage, otherwise wait for the end of rule execution. [default False]
            subject: is specified use this subject instead self.subject
        """
        if subject is None:
            subject = self.subject
        elif isinstance(subject, str):
            subject = subject_factory(subject)

        if extended:
            fn = lambda v: subject.set_ext(property_name, v, use_cache)
        else:
            fn = lambda v: subject.set(property_name, v, muted, use_cache)

        return fn(value)


class SetSubjectExtendedProperty(SetSubjectProperty):
    """
    *Extends* `SetSubjectProperty <https://intro.krules.io/Processing.html#krules_core.base_functions.processing.SetSubjectProperty>`_
    *setting an extended property of the subject(* **extended=True** *). Note that* **muted** *is not present anymore
    in the arguments because an extended property is always muted.
    The extension's aim is to made code more readable.*
    """
    def execute(self,
                property_name: str, value: Any, use_cache: bool =True, subject: Subject = None, **kwargs):
        """

        """
        return super().execute(property_name, value, extended=True, muted=True, use_cache=use_cache, subject=subject)


class SetSubjectProperties(ProcessingFunction):
    """
    *Set multiple properties in subject from dictionary. This is allowed only by using cache and not for
    extended properties. Each property set in that way is muted but it is possible to unmute some of that using*
    **unmuted** *parameter*

    ::

        rulesdata = [
            {
                rulename: "on-device-oboarded-update",
                subscibre_to: "device-onboarded",
                ruledata: {
                    filters: [
                        ...
                        # Check if device has characteristics of an heather
                    ]
                    processing: [
                        SetSubjectProperties(
                            props=lambda: {
                                "device_class": "heather",
                                "on_boarding_tm": datetime.now(),
                            },
                            unmuted=["heather"]
                        )
                        # Thanks to ArgumentProcessor we can use a lambda, without that on_boarding_tm
                        # would be always equal to the Rule instantiation's datetime while we need the execution's one.
                    ]
                }
            }
        ]
    """

    def execute(self, props: dict, unmuted: List[str] = None, use_cache: bool = True, subject: Subject = None):
        """
        Args,
            subject: If specified set properties on this subject
            props: The properties to set
            unmuted: List of property names for which emit property changed events or "*" to unmute all
            subject: use this subject instead self.subject
        """
        if subject is None:
            subject = self.subject
        elif isinstance(subject, str):
            subject = subject_factory(subject)
        if props is None:
            props = {}
        if unmuted is None:
            unmuted = []
        if isinstance(unmuted, str) and unmuted == "*":
            unmuted=list(props.keys())
        for name, value in props.items():
            subject.set(name, value, muted=name not in unmuted, use_cache=use_cache)


class StoreSubject(ProcessingFunction):
    """
    *Store alla subject properties on the subject storage and then flush the cache.
    Usually this happens at the end of the ruleset execution.*
    """

    def execute(self):
        self.subject.store()


class FlushSubject(ProcessingFunction):
    """
    *Remove all subject's properties. It is important tho recall that a subject exists while it has at least a property,
    so* **remove all its properties means remove the subject itself**.

    ::

        rulesdata = [
            {
                rulename: "on-user-unsubscribe-delete-subject",
                subscibre_to: "user-unsubscribed",
                ruledata: {
                    processing: [
                        DeleteProfileFromDB(user_id=lambda subject: subject.user_id),
                        FlushSubject()
                    ]
                }
            },
            {
                rulename: "on-onboard-device-store-properties",
                subscribe_to: "onboard-device",
                ruledata: {
                    processing: [
                        FlushSubject(),
                        SetSubjectProperties(lambda payload: payload["data"]),
                        SetSubjectProperty('status', 'READY'),
                    ],
                },
            },
        ]
    """

    def execute(self):
        self.subject.flush()


#####################################################################################


class Route(ProcessingFunction):
    """
    *Produce an event inside and/or outside the ruleset, for "sending outside" the event we mean to deliver it to the
    dispatcher component.
    By default an event is dispatched outside only if there is no handler defined in the current ruleset.
    However it is possible to change this behavior using* **dispatch_policy**.
    *Available choices are defined in* **krules_core.route.router.DispatchPolicyConst** *as:*
        - **DEFAULT**: *Dispatched outside only when no handler is found in current ruleset;*
        - **ALWAYS**: *Always dispatched outside even if an handler is found and processed in the current ruleset;*
        - **NEVER**: *Never dispatched outside;*
        - **DIRECT**: *Skip to search for a local handler and send outside directly.*

    ::

        from krules_core.route.router.DispatchPolicyConst import DEFAULT, ALWAYS, NEVER, DIRECT
        from krules_core.event_types import SUBJECT_PROPERTY_CHANGED

        # ...

        rulesdata = [
            {
                rulename: "on-device-onboarded-dispatch-added-event",
                subscibre_to: "device-onboarded",
                ruledata: {
                    processing: [
                        # ...
                        # do something with device
                        Route(
                            subject=lambda payload: payload["device_id"],
                            payload=lambda payload: payload["device_data"],
                            event_type="device-added",
                            # no dispatch_policy is provided so will be used the DEFAULT one
                        ),
                    ]
                }
            },
            {
                rulename: "on-position-change-propagate-event",
                subscibre_to: SUBJECT_PROPERTY_CHANGED,
                ruledata: {
                    filters: [
                        OnSubjectPropertyChanged("position")
                    ]
                    processing: [
                        Route(
                            dispatch_policy=DIRECT
                            # In this case we don't specify neither type, nor subject, nor payload.
                            # We use dispatch_policy DIRECT to propagate the received event outside, this increase
                            # efficiency because we want avoid useless check in other rules subscribed to SUBJECT_PROPERTY_CHANGED.
                            #  Note that the rules are processed following the order in which they were defined.
                        )
                    ]
                }
            },
            {
                rulename: "on-temp-change-propagate-event",
                subscibre_to: SUBJECT_PROPERTY_CHANGED,
                ruledata: {
                    filters: [
                        OnSubjectPropertyChanged("temp", value=lambda v: v > 30)
                    ]
                    processing: [
                        Route(
                            event_type="device-overheated"
                            dispatch_policy=ALWAYS
                            # We want to handle device-overheated event both in the current container and outside, for example to send an external notification
                        )
                    ]
                }
            },
            {
                rulename: "on-device-overheated-schedule-check",
                subscribe_to: "device-overheated",
                ruledata: {
                    # ...
                }
            },
        ]
    """

    def execute(self, 
                event_type: str = None, 
                subject: Subject = None,
                payload: dict = None,
                dispatch_policy: str = DispatchPolicyConst.DEFAULT,
                **kwargs):
        """
        Args:
            event_type: The event type. If None use current processing event type [default None]
            subject: The event subject. If None use the current subject [default None]
            payload: The event payload. If None use the current payload [default None]
            dispatch_policy: Define the event dispatch policy as explained before. [default DispatchPolicyConst.DEFAULT]
            kwargs: The event extended properties
        """

        if event_type is None:
            event_type = self.event_type
        if subject is None:
            subject = self.subject
        if payload is None:
            payload = self.payload

        self.router.route(event_type, subject, payload, dispatch_policy=dispatch_policy, **kwargs)


class RaiseException(ProcessingFunction):
    """
    *Force the given exception raising*

    ::

        from .my_custom_exceptions import UnexpectedPayload # supposing we defined a module with custom exceptions

        rulesdata = [
            {
                rulename: "on-unexpected-payload-raise-exception",
                subscibre_to: "device-onboarded",
                ruledata: {
                    filters: [
                        Return(lambda payload: "device_id" not in payload)
                    ]
                    processing: [
                        RaiseException(
                            UnexpectedPayload("device_id missing!")
                        )
                    ]
                }
            },
        ]
    """

    def execute(self, ex):
        """
        Args:
            ex: The exception to be raised
        """

        raise ex

