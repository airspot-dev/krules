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


class Returns(RuleFunctionBase):
    """
    Simply returns expression
    """

    def execute(self, expression):
        """
        Args:
            expression: We expect expression to be something callable that can be evaluated
        """
        return expression


class IsTrue(Returns):
    """
    True if True
    """

    def execute(self, expression):
        """
        Args:
            expression: We expect expression to be something callable that can be evaluated as a boolean
        """

        return bool(super().execute(expression))


class IsFalse(Returns):
    """
    True if False
    """

    def execute(self, expression):
        """
        Args:
            expression: We expect expression to be something callable that can be evaluated as a boolean
        """

        return not bool(super().execute(expression))


class SubjectNameMatch(RuleFunctionBase):
    """
    Checks if the subject's name matches the **regular expression**
    """

    def execute(self, regex, payload_dest="subject_match"):
        """
        Args:
            regex: Check expression
            payload_dest: Name of the key in the payload where the value of any groups contained in the expression is saved
        """
        import re
        match = re.search(regex, self.subject.name)
        if match is None:
            return False
        self.payload[payload_dest] = match.groupdict()
        return True


class SubjectNameDoesNotMatch(SubjectNameMatch):
    """
    Opposite of CheckSubjectNameMatch
    """

    def execute(self, regex, **kwargs):  # TODO: best inheritage support (**kwargs satisfy base class signature)

        return not super().execute(regex)


class CheckSubjectProperty(RuleFunctionBase):
    """
    Check the value of a property in the subject
    If the property does not exists returns False
    """

    def execute(self, property_name, property_value=lambda _none_: None, extended=False, cached=True):
        """
        Args:
            property_name: The name of the property
            property_value: Value to compare. If omitted, only the presence of the property is checked.
              If a callable is provided, this is invoked (optionally) with the property value
            See tests for examples
            extended: If True, check extended property
            cached: If False it checks the actual value on the storage backend bypassing the cached value
        """
        if property_name not in self.subject:
            return False
        _get = extended and self.subject.get_ext or self.subject.get
        if inspect.isfunction(property_value):
            sign = inspect.signature(property_value)
            if str(sign) == '(_none_)':
                return True
            n_args = len(sign.parameters)
            args = []
            if n_args > 0:
                args.append(_get(property_name, cached=cached))
            # if n_args > 1:
            #     args.append(self.payload)
            return property_value(*args)
        return _get(property_name, cached=cached) == property_value


class PayloadMatch(RuleFunctionBase):
    """
    It allows to process the payload with a jsonpath expression to check its content and possibly isolate part of it
    in a target variable
    """

    def execute(self, jp_expr, match_value=lambda _none_: None, payload_dest=None, single_match=False):
        """
        Args:
            jp_expr: Jsonpath expression
            payload_dest: If specified store the epression match result in that key in payload
            match_value: It can be both the expected value of the jsonpath expression processing or a boolean function
            that handles the expression result.
            single_match: if True produce a single value as result, a list of values otherwise

        >>> payload = {
        >>>             "user": "admin",
        >>>             "data": [{"id": 1, "value": 200}, {"id": 2, "value": 90}, {"id": 3, "value": 250}]}
        >>>         }
        >>> PayloadMatch("$.user", "admin")
        >>> False
        >>> PayloadMatch("$.user", "admin", single_match=True)
        >>> True
        >>> PayloadMatch("$.data[?@.value>100]")
        >>> True
        >>> PayloadMatch("$.data[?@.value>100]", [1, 3])
        >>> False
        >>> PayloadMatch("$.data[?@.value>100]", lambda x: len(x) == 2)
        >>> True
        """

        import jsonpath_rw_ext as jp

        matched = False
        fn = jp.match
        if single_match:
            fn = jp.match1

        match = fn(jp_expr, self.payload)
        if match is not None and len(match):
            matched = True

        if payload_dest:
            self.payload[payload_dest] = match

        if inspect.isfunction(match_value):
            sign = inspect.signature(match_value)
            if str(sign) != '(_none_)':
                n_args = len(sign.parameters)
                args = []
                if n_args > 0:
                    args.append(match)

                matched = match_value(*args)
        else:
            matched = match == match_value

        return matched


class PayloadMatchOne(PayloadMatch):
    """
    Same as CheckPayloadJPMatch but expects just one element as result
    """

    def execute(self, jp_expr, match_value=lambda _none_: None, payload_dest=None, **kwargs):
        """
        Args:
            jp_expr: Jsonpath expression
            payload_dest: Destination key in payload
        """
        return super().execute(jp_expr, match_value, payload_dest, True)


class SubjectPropertyChanged(RuleFunctionBase):
    """
    Catch the event subject property changed
    """

    def execute(self, property_name, value=lambda _none_: None, old_value=lambda _none_: None):
        """
        Args:
            property_name: Name of property changed. Accept callable receiving (optionally) the property name, In that
               case it must returns a boolean
            value: If not a callable the value is compared, otherwise it can receive no parameters,
               or the value of the property and eventually also the previous value of the property (old_value).
               It must returns a boolean
            old_value: If not a callable the value is compared, otherwise it receives (optionally) the old_value and
               must returns a boolean
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
                if n_args == 0:
                    matched = self.payload[PayloadConst.VALUE] == value()
                elif n_args == 1:
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
                if n_args == 0:
                    matched = self.payload[PayloadConst.OLD_VALUE] == old_value()
                elif n_args == 1:
                    matched = old_value(self.payload[PayloadConst.OLD_VALUE])
                else:
                    raise TypeError("takes at most two arguments (received {})".format(n_args))
        else:
            matched = self.payload[PayloadConst.OLD_VALUE] == old_value

        if not matched:
            return False

        return True
