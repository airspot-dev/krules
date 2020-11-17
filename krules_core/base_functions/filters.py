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
import json

from krules_core.subject import PayloadConst

from krules_core.base_functions import RuleFunctionBase
import inspect


class Filter(RuleFunctionBase):
    """
    *Evaluates a boolean expression and returns its value.*
    *The best way to exploit it is to use it in combination with* `Argument Processors <https://intro.krules.io/ArgumentProcessors.html>`_.

    ::

        {
            rulename: "filtered-rules",
            subscibre_to: "...",
            ruledata: {
                filters: [
                    Filter(
                        lambda payload:(
                            "my-label" in payload["object"]["metadata"].get("labels", {})
                        )
                    ),
                ]
                processing: [
                    ...
                ]
            }
        }

    """

    def execute(self, value):
        """
        Args:
            value: Boolean expression which will be evaluated
        """
        return value


class SubjectNameMatch(RuleFunctionBase):
    """
    *Return True if the subject's name matches the given regular expression*

    ::

        {
            rulename: "...",
            subscibre_to: "...",
            ruledata: {
                filters: [
                    SubjectNameMatch(r"^user\|(?P<user_id>.+)", payload_dest="user_id"),
                ]
                processing: [
                    ...
                ]
            }
        }
    """

    def execute(self, regex, payload_dest="subject_match"):
        """
        Args:
            regex: Regular expression which will be evaluated
            payload_dest: Name of the key in the payload where the value of any groups contained in the expression will be saved saved
        """
        import re
        match = re.search(regex, self.subject.name)
        if match is None:
            return False
        self.payload[payload_dest] = match.groupdict()
        return True


class SubjectNameDoesNotMatch(SubjectNameMatch):
    """
    *Return True if the subject's name does not match the given regular expression*
    """

    def execute(self, regex, **kwargs):  # TODO: best inheritage support (**kwargs satisfy base class signature)
        """
        Args:
            regex: Regular expression which will be evaluated
        """

        return not super().execute(regex)


class CheckSubjectProperty(RuleFunctionBase):
    """
    *Returns True if the given subject property exists and, if provided, match the given value.*

    ::

        {
            rulename: "...",
            subscibre_to: "...",
            ruledata: {
                filters: [
                    CheckSubjectProperty(
                        "last_update",
                        property_value=lambda payload:(
                            lambda value: value < payload.get("update_time")
                        )
                    ),
                ]
                processing: [
                    ...
                ]
            }
        }
    """

    def execute(self, property_name, property_value=lambda _none_: None, extended=False, use_cache=True):
        """
        Args:
            property_name: The name of the property
            property_value(optional): Could be the expected property value or a callable which takes the actual property value as unique parameter. It is possible to exploit the `Argument Processors <https://intro.krules.io/ArgumentProcessors.html>`_ to get the expected property value using nested lambda (as in exmaple).
            extended: If True, check extended property [default False]
            use_cache: If False it checks the actual value on the storage backend bypassing the cached value [default True]
        """

        if (property_name not in self.subject and not extended) or (
                extended and property_name not in self.subject.get_ext_props()):
            return False

        _get = extended and self.subject.get_ext or self.subject.get
        if inspect.isfunction(property_value):
            sign = inspect.signature(property_value)
            if str(sign) == '(_none_)':
                return True
            return property_value(_get(property_name, use_cache=use_cache))
        return _get(property_name, use_cache=use_cache) == property_value


class PayloadMatch(RuleFunctionBase):
    """
    *Processes the payload with a given jsonpath expression to check its content.*


    ::

        # event payload = {
        #     "user": "admin",
        #     "skills": [{"id": 1, "rating": 85}, {"id": 2, "value": 53}, {"id": 3, "value": 98}]}
        # }


        {
            rulename: "...",
            subscibre_to: "...",
            ruledata: {
                filters: [
                    PayloadMatch("$.user", "admin"), # return False because with single_match = False match result is always a list
                ]
                processing: [
                    ...
                ]
            }
        },
        {
            rulename: "...",
            subscibre_to: "...",
            ruledata: {
                filters: [
                    PayloadMatch("$.user", "admin", single_match=True), # return True
                ]
                processing: [
                    ...
                ]
            }
        },
        {
            rulename: "...",
            subscibre_to: "...",
            ruledata: {
                filters: [
                    PayloadMatch("$.data[?@.rating>80]", lambda x: len(x) == 2, payload_dest="qualified_skills")
                ]
                processing: [
                    ...
                ]
            }
        },


class PayloadMatchOne(PayloadMatch):
    """
    *Extends PayloadMatch defaulting single_match to True and so expects just one element as result*

    ::

        {
            rulename: "...",
            subscibre_to: "...",
            ruledata: {
                filters: [
                    PayloadMatchOne("$.user", "admin"), # return True, it is the same as PayloadMatch("$.user", "admin", single_match=True)
                ]
                processing: [
                    ...
                ]
            }
        }
    """

    def execute(self, jp_expr, match_value=lambda _none_: None, payload_dest=None, **kwargs):
        """
        Args:
            jp_expr: Jsonpath expression
            payload_dest: Destination key in payload
        """
        return super().execute(jp_expr, match_value, payload_dest, True)


class OnSubjectPropertyChanged(RuleFunctionBase):
    """

    *Specific function to filter* **subject-property-changed** *event.
    This event is produced whenever a subject property changes and its data contains the property name, the new property value and the old one.*

    ::

        ☁️  cloudevents.Event
        Validation: valid
        Context Attributes,
          specversion: 1.0
          type: subject-property-changed
          source: my-ruleset
          subject: foo
          id: bd198e83-9d7e-4e93-a9ae-aa21a40383c6
          time: 2020-06-16T08:16:57.340692Z
          datacontenttype: application/json
        Extensions,
          knativearrivaltime: 2020-06-16T08:16:57.346535873Z
          originid: bd198e83-9d7e-4e93-a9ae-aa21a40383c6
          propertyname: count
          traceparent: 00-d571530282362927f824bae826e1fa36-a52fceb915060653-00
        Data,
          {
            "property_name": "count",
            "old_value": 0,
            "value": 1
          }

    *It is important to note that the property name is also present also in the event's extensions and can therefore be used as a filter in a Trigger to intercept changes only of a specific property.*

    ::

        apiVersion: eventing.knative.dev/v1
        kind: Trigger
        metadata:
          name: on-count-change-trigger
        spec:
          filter:
            attributes:
              propertyname: count
              type: subject-property-changed
          subscriber:
            ref:
              apiVersion: v1
              kind: Service
              name: on-count-change-handler

    *This function allows you to exec your rule only when a specific property changes and, optionally, only for a specific current or previous value of it.*

    ::

        {
            rulename: "...",
            subscibre_to: "...",
            ruledata: {
                filters: [
                    SetSubjectProperty("count", lambda x: x + 1), # Since in this case the event will be handled within the ruleset itself,
                                                                  # it is not necessary to define any trigger to intercept it
                ]
                processing: [
                    ...
                ]
            }
        },
        {
            rulename: "...",
            subscibre_to: "subject-property-changed",
            ruledata: {
                filters: [
                    SubjectPropertyChanged("count"), # Exec processing section each time property count changes
                ]
                processing: [
                    ...
                ]
            }
        },
        {
            rulename: "...",
            subscibre_to: "subject-property-changed",
            ruledata: {
                filters: [
                    SubjectPropertyChanged(
                        "count",
                        value=lambda v: v%2 == 0
                    ), # Exec processing section each time a new even value is assigned to property count
                ]
                processing: [
                    ...
                ]
            }
        },
        {
            rulename: "...",
            subscibre_to: "subject-property-changed",
            ruledata: {
                filters: [
                    SubjectPropertyChanged("count", old_value=0), # Exec processing section each time property count changes and
                                                                  # its old value is equal to 0
                ]
                processing: [
                    ...
                ]
            }
        },
        {
            rulename: "...",
            subscibre_to: "subject-property-changed",
            ruledata: {
                filters: [
                    SubjectPropertyChanged(
                        "count",
                        value=lambda v, o: v > 10 && o%2 == 1
                    ), # Exec processing section each time a new value greater than 10 is assigned to property count and its last value was odd
                ]
                processing: [
                    ...
                ]
            }
        },
    """

    def execute(self, property_name, value=lambda _none_: None, old_value=lambda _none_: None):
        """
        Args:
            property_name: Name of the changed property. Could be a string, a callable with no args which returns the property name or a boolean callable which accepts the property name as unique parameter
            value: Could be the expected value or  a boolean callable which takes as arguments just the new property value or the new value and the previous one. It is possible to exploit the `Argument Processors <https://intro.krules.io/ArgumentProcessors.html>`_ to get the expected property value.
            old_value: Could be the expected previous property value or a boolean callable which takes as arguments the previous property value. It is possible to exploit the `Argument Processors <https://intro.krules.io/ArgumentProcessors.html>`_ to get the expected old property value.
        """

        # property_name
        if inspect.isfunction(property_name):
            sign = inspect.signature(property_name)
            n_args = len(sign.parameters)
            if n_args == 0:
                matched = self.payload[PayloadConst.PROPERTY_NAME] == property_name()
            elif n_args == 1:
                matched = property_name(self.payload[PayloadConst.PROPERTY_NAME])
            else:
                raise TypeError("takes at most two arguments (received {})".format(n_args))
        else:
            matched = self.payload[PayloadConst.PROPERTY_NAME] == property_name

        if not matched:
            return False

        # value
        if inspect.isfunction(value):
            sign = inspect.signature(value)
            if str(sign) != '(_none_)':
                n_args = len(sign.parameters)
                if n_args == 1:
                    matched = value(self.payload[PayloadConst.VALUE])
                elif n_args == 2:
                    args = [self.payload[PayloadConst.VALUE], self.payload[PayloadConst.OLD_VALUE]]  # for IDE happiness
                    matched = value(*args)
                else:
                    raise TypeError("takes at most three arguments (received {})".format(n_args))
        else:
            matched = self.payload[PayloadConst.VALUE] == value

        if not matched:
            return False

        # old_value
        if inspect.isfunction(old_value):
            sign = inspect.signature(old_value)
            if str(sign) != '(_none_)':
                n_args = len(sign.parameters)
                if n_args == 1:
                    matched = old_value(self.payload[PayloadConst.OLD_VALUE])
                else:
                    raise TypeError("takes at most two arguments (received {})".format(n_args))
        else:
            matched = self.payload[PayloadConst.OLD_VALUE] == old_value

        if not matched:
            return False

        return True
