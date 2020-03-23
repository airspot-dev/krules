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


from krules_core.subject import PayloadConst
from krules_core.base_functions import RuleFunctionBase


class IsTrue(RuleFunctionBase):

    def execute(self, value):

        return value is True


class IsFalse(RuleFunctionBase):

    def execute(self, value):

        return value is False

class ForAction(RuleFunctionBase):

    """
    For testing purpose. Check action
    """

    def execute(self, action):

        return self.action == action


# TODO: tests
class Check(RuleFunctionBase):

    def execute(self, expr):

        # TODO: bug!!! does not work with with_subject
        return expr


With = Check

class CheckPayload(RuleFunctionBase):

    def execute(self, func):

        return func(self.payload)


WithPayload = CheckPayload


# TODO: refactor: CheckSubject
class SubjectCheck(RuleFunctionBase):

    def execute(self, func):

        return func(self.subject)


# TODO: make effective
class CheckSubject(SubjectCheck):
    pass


# TODO: unit tests
class SubjectMatch(RuleFunctionBase):

    def execute(self, regex, payload_dest="subject_match"):
        import re
        match = re.search(regex, self.subject.name)
        if match is None:
            return False
        self.payload[payload_dest] = match.groupdict()
        return True


class SubjectDoesNotMatch(RuleFunctionBase):

    def execute(self, regex):
        import re
        match = re.search(regex, self.subject.name)
        if match is None:
            return True
        return False


# TODO: unit tests
class CheckSubjectPropertyValue(RuleFunctionBase):

    def execute(self, property_name, property_value, default=False):

        if property_name not in self.subject:
            #setattr(self.subject, property_name, None)
            if default is True:
                return True
            return False

        return getattr(self.subject, property_name) == property_value



# TODO: unit tests
class CheckSubjectPropertyValueIn(RuleFunctionBase):

    def execute(self, property_name, property_values, default=False):

        if property_name not in self.subject:
            if default is True:
                return True
            return False

        return getattr(self.subject, property_name) in property_values


# TODO: unit tests
class CheckSubjectPropertyValueNotIn(RuleFunctionBase):

    def execute(self, property_name, property_values, default=True):

        if property_name not in self.subject:
            #setattr(self.subject, property_name, None)
            #return False
            return default

        return getattr(self.subject, property_name) not in property_values


# TODO: unit tests
class CheckPayloadJPMatch(RuleFunctionBase):

    def execute(self, jp_expr, payload_dest=None, single_match=False):

        import jsonpath_rw_ext as jp

        matched = False
        fn = jp.match
        if single_match:
            fn = jp.match1

        match =fn(jp_expr, self.payload)
        if match is not None and len(match):
            matched = True

        if payload_dest:
            self.payload[payload_dest] = match

        return matched


# TODO: unit tests
class CheckPayloadPropertyValue(RuleFunctionBase):

    def execute(self, property_name, property_value):

        if property_name not in self.payload:
            return False

        if self.payload[property_name] != property_value:
            return False

        return True


# TODO: unit tests
class CheckPayloadPropertyValueIn(RuleFunctionBase):

    def execute(self, property_name, property_values):

        if property_name not in self.payload:
            return False

        if self.payload[property_name] in property_values:
            return True

        return False


# TODO: unit tests
class CheckPayloadPropertyValueNotIn(RuleFunctionBase):

    def execute(self, property_name, property_values):

        if property_name not in self.payload:
            return False

        if self.payload[property_name] in property_values:
            return False

        return True


# TODO: unit tests
class CheckPayloadPropertyValueMatch(RuleFunctionBase):

    def execute(self, jp_expr, value_re, payload_dest=None):
        import jsonpath_rw_ext as jp
        import re



        if not jp_expr.startswith("$."):
            jp_expr = "$."+jp_expr

        value = jp.match1(jp_expr, self.payload)
        if value is None:
            return False

        m = re.match(value_re, value)

        if m is None:
            return False

        if payload_dest:
            _dict = m.groupdict()
            if len(_dict):
                self.payload[payload_dest] = _dict
                return True

            _groups = m.groups()
            _len = len(_groups)
            if _len:
                if _len == 1:
                    self.payload[payload_dest] = _groups[0]
                else:
                    self.payload[payload_dest] = _groups

        return True


# TODO: unit tests
class CheckPayloadPropertyValueDoesNotMatch(RuleFunctionBase):

    def execute(self, jp_expr, value_re):
        import jsonpath_rw_ext as jp
        import re

        if not jp_expr.startswith("$."):
            jp_expr = "$."+jp_expr

        value = jp.match1(jp_expr, self.payload)
        if value is None:
            return True

        m = re.match(value_re, value)

        if m is None:
            return True

        return False


# TODO: unit tests
class OnSubjectPropertyChanged(RuleFunctionBase):

    def execute(self, property_name, not_null=True):

        assert(isinstance(not_null, bool))  # prevent common programming errors

        _property_name = self.payload.get(PayloadConst.PROPERTY_NAME, None)
        if _property_name is None:
            return False

        match = _property_name == property_name
        if match and not_null == True:
            if self.payload[PayloadConst.VALUE] is None:
                return False
        return match


# TODO: unit tests
class OnSubjectPropertyChangedIn(RuleFunctionBase):

    def execute(self, *property_names):

        _property_name = self.payload.get(PayloadConst.PROPERTY_NAME, None)
        if _property_name is None:
            return False

        return _property_name in property_names


# TODO: unit tests
class OnSubjectPropertyChangedNotIn(RuleFunctionBase):

    def execute(self, *property_names):

        _property_name = self.payload.get(PayloadConst.PROPERTY_NAME, None)
        if _property_name is None:
            return True

        return _property_name not in property_names


# TODO: unit tests
class OnSubjectPropertyChangedValue(RuleFunctionBase):

    def execute(self, property_name, property_value):

        _property_name = self.payload.get(PayloadConst.PROPERTY_NAME, None)
        if _property_name is None:
            return False
        _property_value = self.payload.get(PayloadConst.VALUE, None)

        return _property_name == property_name and _property_value == property_value


# TODO: unit tests
class OnSubjectPropertyChangedValueIn(RuleFunctionBase):

    def execute(self, property_name, property_value):

        _property_name = self.payload.get(PayloadConst.PROPERTY_NAME, None)
        if _property_name is None:
            return False
        _property_value = self.payload.get(PayloadConst.VALUE, None)

        return _property_name == property_name and _property_value in property_value


# TODO: unit tests
class OnSubjectPropertyChangedValueExpr(RuleFunctionBase):

    def execute(self, property_name, expr):

        _property_name = self.payload.get(PayloadConst.PROPERTY_NAME, None)
        if _property_name is None:
            return False
        _property_value = self.payload.get(PayloadConst.VALUE, None)

        return expr(_property_value)


# TODO: unit tests
class OnSubjectPropertyChangedTransition(RuleFunctionBase):

    def execute(self, property_name, value_from, value_to):
        _property_name = self.payload.get(PayloadConst.PROPERTY_NAME, None)
        if _property_name is None:
            return False

        _value_from = self.payload.get(PayloadConst.OLD_VALUE)
        _value_to = self.payload.get(PayloadConst.VALUE)

        return _property_name == property_name and _value_from == value_from and _value_to == value_to


# TODO: unit tests
class ExceptionIfOrTrue(RuleFunctionBase):

    def execute(self, condition, ex):

        if condition:
            raise ex

        return True
