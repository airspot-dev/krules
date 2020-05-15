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
import pytest

from krules_core import RuleConst
from krules_core.base_functions import RuleFunctionBase, inspect
from krules_core.core import RuleFactory
from krules_core.providers import message_router_factory, subject_factory

filters = RuleConst.FILTERS
processing = RuleConst.PROCESSING
rule_name = RuleConst.RULE_NAME
processed = RuleConst.PROCESSED


def test_simple_callable():

    class SimpleSet(RuleFunctionBase):

        def execute(self, arg1, arg2, arg3, arg4, arg5):

            self.payload["arg1"] = arg1
            self.payload["arg2"] = arg2
            self.payload["arg3"] = arg3
            self.payload["arg4"] = arg4
            self.payload["arg5"] = arg5

    RuleFactory.create(
        "test-simple-callable",
        subscribe_to="test-argprocessors-callables",
        ruledata={
            processing: [
                SimpleSet(lambda: 1, 2, arg3=lambda: 3, arg4=4, arg5=lambda p: "I'll never be called")
            ]
        }
    )

    payload = {}
    message_router_factory().route("test-argprocessors-callables", "test-0", payload)

    assert payload["arg1"] == 1
    assert payload["arg2"] == 2
    assert payload["arg3"] == 3
    assert payload["arg4"] == 4
    assert inspect.isfunction(payload["arg5"])


def test_with_self():

    class WithSelfSet(RuleFunctionBase):

        def execute(self, arg1, arg2, arg3):

            self.payload["arg1"] = arg1
            self.payload["arg2"] = arg2
            self.payload["arg3"] = arg3

    RuleFactory.create(
        "test-with-self",
        subscribe_to="test-argprocessors-self",
        ruledata={
            processing: [
                WithSelfSet(lambda self: self.payload["value_from"],
                            arg2=lambda self: self.subject.get("value_from"),
                            arg3=lambda p: "I'll never be called")
            ]
        }
    )

    payload = {"value_from": 1}
    subject = subject_factory("test-1")

    subject.set("value_from", 2)

    message_router_factory().route("test-argprocessors-self", subject, payload)

    assert payload["arg1"] == 1
    assert payload["arg2"] == 2
    assert inspect.isfunction(payload["arg3"])


def test_with_payload_and_subject():

    class WithPayloadSet(RuleFunctionBase):

        def execute(self, arg1, arg2, arg3):

            self.payload["arg1"] = arg1
            self.payload["arg2"] = arg2
            self.payload["arg3"] = arg3

    RuleFactory.create(
        "test-with-payload-and-subject",
        subscribe_to="test-argprocessors-payload-and-subject",
        ruledata={
            processing: [
                WithPayloadSet(lambda payload: payload["value_from"],
                               arg2=lambda subject: subject.get("value_from"),
                               arg3=lambda p: "I'll never be called")
            ]
        }
    )

    _payload = {"value_from": 1}
    _subject = subject_factory("test-1")

    _subject.set("value_from", 2)

    message_router_factory().route("test-argprocessors-payload-and-subject", _subject, _payload)

    assert _payload["arg1"] == 1
    assert _payload["arg2"] == 2
    assert inspect.isfunction(_payload["arg3"])


def test_extend_jp_match():

    import jsonpath_rw_ext as jp
    from krules_core.arg_processors import processors

    class JPMatchSet(RuleFunctionBase):

        def execute(self, values, arg2):

            self.payload["values"] = values
            self.payload["elem-2"] = arg2

    class JPPayloadMatchBase:

        def __init__(self, expr):
            self._expr = expr

        @classmethod
        def interested_in(cls, arg):
            return isinstance(arg, cls)

    class jp_match(JPPayloadMatchBase):

        @staticmethod
        def process(instance, arg):
            return jp.match(arg._expr, instance.payload)

    class jp_match1(JPPayloadMatchBase):

        @staticmethod
        def process(instance, arg):
            return jp.match1(arg._expr, instance.payload)

    processors.extend((jp_match, jp_match1))

    RuleFactory.create(
        "test-with-jp-expr",
        subscribe_to="test-argprocessors-jp-match",
        ruledata={
            processing: [
                JPMatchSet(jp_match("$.elems[*].value"),
                           jp_match1("$.elems[?id==2]"))
            ]
        }
    )

    payload = {
        "elems": [
            {
                "id": 1,
                "value": "a"
            },
            {
                "id": 2,
                "value": "b"
            }
        ]
    }

    message_router_factory().route("test-argprocessors-jp-match", "test-0", payload)

    assert payload["values"] == ['a', 'b']
    assert payload["elem-2"]["id"] == 2 and payload["elem-2"]["value"] == "b"