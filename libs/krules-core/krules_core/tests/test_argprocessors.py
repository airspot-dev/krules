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
from rx import subject as rx_subject
from dependency_injector import providers

from krules_core.arg_processors import BaseArgProcessor
from krules_core import RuleConst
from krules_core.base_functions import RuleFunctionBase, inspect
from krules_core.core import RuleFactory
from krules_core.providers import event_router_factory, subject_factory, proc_events_rx_factory
from rx import subject

filters = RuleConst.FILTERS
processing = RuleConst.PROCESSING
rulename = RuleConst.RULENAME
passed = RuleConst.PASSED

@pytest.fixture
def router():
    router = event_router_factory()
    router.unregister_all()
    proc_events_rx_factory.override(providers.Singleton(rx_subject.ReplaySubject))

    return event_router_factory()

def _assert(expr):
    assert expr
    return True

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
        data={
            processing: [
                SimpleSet(lambda: 1, 2, arg3=lambda: 3, arg4=4, arg5=lambda p: "I'll never be called")
            ]
        }
    )

    payload = {}
    event_router_factory().route("test-argprocessors-callables", "test-0", payload)

    proc_events_rx_factory().subscribe(
        lambda x: x[rulename] == "test-simple-callable" and _assert(
            x[processing][0]["args"][0] == 1
            and x[processing][0]["kwargs"]["arg3"] == 3
            and x[processing][0]["kwargs"]["arg4"] == 4
            and isinstance(x[processing][0]["kwargs"]["arg5"], str)
        )
    )

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
        data={
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

    event_router_factory().route("test-argprocessors-self", subject, payload)
    proc_events_rx_factory().subscribe(
        lambda x: x[rulename] == "test-with-self" and _assert(
            x[processing][0]["args"][0] == 1
            and x[processing][0]["kwargs"]["arg2"] == 2
            and isinstance(x[processing][0]["kwargs"]["arg3"], str))
    )

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
        data={
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

    event_router_factory().route("test-argprocessors-payload-and-subject", _subject, _payload)

    proc_events_rx_factory().subscribe(
        lambda x: x[rulename] == "test-with-payload-and-subject" and _assert(
            x[processing][0]["args"][0] == 1 and x[processing][0]["kwargs"]["arg2"] == 2
            and isinstance(x[processing][0]["kwargs"]["arg3"], str))
    )

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

        def match(self, instance):
            raise NotImplementedError()

    class jp_match(JPPayloadMatchBase):

        def match(self, instance):
            return jp.match(self._expr, instance.payload)

    class jp_match1(JPPayloadMatchBase):

        def match(self, instance):
            return jp.match1(self._expr, instance.payload)

    class JPProcessor(BaseArgProcessor):

        @staticmethod
        def interested_in(arg):
            return isinstance(arg, JPPayloadMatchBase)

        def process(self, instance):
            return self._arg.match(instance)

    processors.append(JPProcessor)

    RuleFactory.create(
        "test-with-jp-expr",
        subscribe_to="test-argprocessors-jp-match",
        data={
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

    event_router_factory().route("test-argprocessors-jp-match", "test-0", payload)

    proc_events_rx_factory().subscribe(
        lambda x: x[rulename] == "test-with-jp-expr" and _assert(
            x[processing][0]["args"][0] == ['a', 'b']
            and x[processing][0]["args"][1] == {"id": 2, "value": "b"})
    )

    assert payload["values"] == ['a', 'b']
    assert payload["elem-2"]["id"] == 2 and payload["elem-2"]["value"] == "b"