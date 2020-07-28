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
import rx
from dependency_injector import providers
from krules_core import RuleConst
from krules_core.base_functions import UpdatePayload, SetPayloadProperties, SetPayloadProperty, SetSubjectProperty, \
    SubjectPropertyChanged, SetSubjectExtendedProperty, SetSubjectPropertySilently, StoreSubjectProperty, \
    RuleFunctionBase, StoreSubjectPropertySilently, SetSubjectProperties, IncrementSubjectProperty, \
    DecrementSubjectProperty, IncrementSubjectPropertySilently, DecrementSubjectPropertySilently

from krules_core.core import RuleFactory
from .. import get_value_from_payload_diffs

from krules_core.providers import (
    event_router_factory,
    proc_events_rx_factory,
    subject_factory,
    subject_storage_factory)

counter = 0
asserted = []


@pytest.fixture
def subject():
    global counter
    counter += 1

    return subject_factory('test-subject-{0}'.format(counter)).flush()


@pytest.fixture
def router():
    router = event_router_factory()
    router.unregister_all()
    proc_events_rx_factory.override(providers.Singleton(rx.subjects.ReplaySubject))

    return event_router_factory()


@pytest.fixture
def asserted():
    global asserted
    asserted = []
    return asserted


filters = RuleConst.FILTERS
processing = RuleConst.PROCESSING
rulename = RuleConst.RULENAME
processed = RuleConst.PROCESSED


def _assert(name, expr, msg="test failed"):
    global asserted
    assert expr, msg
    asserted.append(name)


def test_payload_functions(subject, router, asserted):
    payload = {
        "k1": "val1",
        "k2": {"k2a": 1,
               "k2b": {"a": 1, "b": 2}}
    }

    RuleFactory.create(
        "test-alter-payload",
        subscribe_to="test-alter-payload",
        data={
            processing: [
                UpdatePayload({
                    "k2": {"k2b": {"b": 3, "c": 4}},
                    "k3": 3,
                }),
                SetPayloadProperties(k1=0, k3=lambda v: v+1, k4=lambda *args: len(args) and args[0]+1 or -1),
                SetPayloadProperty("k4", lambda *args: len(args) and args[0]+1 or -1)
            ]
        }
    )

    proc_events_rx_factory().subscribe(
        lambda x: x[rulename] == "test-alter-payload" and _assert(
            "test-update-1",
            get_value_from_payload_diffs("k3", x[processing][0]["payload_diffs"]) == 3 and
            "a" in x["payload"]["k2"]["k2b"] and x["payload"]["k2"]["k2b"]["a"] == payload["k2"]["k2b"]["a"] and
            not get_value_from_payload_diffs("k2/k2b/a", x[processing][0]["payload_diffs"]) and
            get_value_from_payload_diffs("k2/k2b/b", x[processing][0]["payload_diffs"]) == 3 and
            get_value_from_payload_diffs("k2/k2b/c", x[processing][0]["payload_diffs"]) == 4 and
            not get_value_from_payload_diffs("k2", x[processing][0]["payload_diffs"], default_value=None)
        )
    )
    proc_events_rx_factory().subscribe(
        lambda x: x[rulename] == "test-alter-payload" and _assert(
            "test-update-2",
            get_value_from_payload_diffs("k1", x[processing][1]["payload_diffs"]) == 0 and
            get_value_from_payload_diffs("k3", x[processing][1]["payload_diffs"]) == 4 and
            get_value_from_payload_diffs("k4", x[processing][1]["payload_diffs"]) == -1
        )
    )
    proc_events_rx_factory().subscribe(
        lambda x: x[rulename] == "test-alter-payload" and _assert(
            "test-update-3",
            get_value_from_payload_diffs("k4", x[processing][1]["payload_diffs"]) == 0
        )
    )

    router.route("test-alter-payload", subject, payload)

    assert "test-update-1" in asserted
    assert "test-update-2" in asserted


def test_subject_functions(subject, router, asserted):

    class _CheckStoredValue(RuleFunctionBase):

        def execute(self, prop, expected_value):
            if not subject_storage_factory(self.subject.name).is_concurrency_safe():
                return True   # skip test
            subject = subject_factory(self.subject.name)
            return subject.get(prop, cached=False) == expected_value


    from datetime import datetime
    RuleFactory.create(
        "test-set-subject-property",
        subscribe_to="test-set-subject-property",
        data={
            processing: [
                SetSubjectProperty("dt_prop", lambda: datetime.now().isoformat()),  # no args
                SetSubjectProperty("my_prop", 1),
                SetSubjectProperty("my_prop", lambda v: v+10),
                SetSubjectPropertySilently("something_to_say", False),
                StoreSubjectProperty("my_prop_2", 2),
                _CheckStoredValue("my_prop_2", 2),
                StoreSubjectPropertySilently("my_prop_3", 3),
                _CheckStoredValue("my_prop_3", 3),
                SetSubjectExtendedProperty("my_ext_prop", "extpropvalue"),
                SetSubjectProperties({
                    "my_prop_4": 4,
                    "my_silent_prop_5": 5
                }, unmuted=["my_prop_4"]),
                IncrementSubjectProperty("my_prop_4"),
                _CheckStoredValue("my_prop_4", 1),  # cached property in not considered
                DecrementSubjectProperty("my_prop_4", amount=1.5),
                IncrementSubjectPropertySilently("my_silent_prop_6"),
                DecrementSubjectPropertySilently("my_silent_prop_6"),
            ]
        }
    )
    from krules_core import types
    RuleFactory.create(
        "test-non-muted-property",
        subscribe_to=types.SUBJECT_PROPERTY_CHANGED,
        data={
            filters: [
                SubjectPropertyChanged("my_prop", lambda value, old_value: value == 1 and old_value is None)
            ]
        }
    )
    RuleFactory.create(
        "test-muted-property",
        subscribe_to=types.SUBJECT_PROPERTY_CHANGED,
        data={
            filters: [
                SubjectPropertyChanged("something_to_say")
            ]
        }
    )
    RuleFactory.create(
        "test-direct-property",
        subscribe_to=types.SUBJECT_PROPERTY_CHANGED,
        data={
            filters: [
                SubjectPropertyChanged("my_prop_2", lambda value, old_value: value == 2 and old_value is None)
            ]
        }
    )
    RuleFactory.create(
        "test-muted-direct-property",
        subscribe_to=types.SUBJECT_PROPERTY_CHANGED,
        data={
            filters: [
                SubjectPropertyChanged("my_prop_3")
            ]
        }
    )
    RuleFactory.create(
        "test-multi-set-properties-unmuted",
        subscribe_to=types.SUBJECT_PROPERTY_CHANGED,
        data={
            filters: [
                SubjectPropertyChanged("my_prop_4")
            ]
        }
    )
    RuleFactory.create(
        "test-multi-set-properties-muted",   # never processed
        subscribe_to=types.SUBJECT_PROPERTY_CHANGED,
        data={
            filters: [
                SubjectPropertyChanged(lambda p: p in ("my_silent_prop_5", "my_silent_prop_6"))
            ]
        }
    )

    proc_events_rx_factory().subscribe(
        lambda x: x[rulename] == "test-set-subject-property" and _assert(
            x[rulename],
            x[processed]
        )
    )
    proc_events_rx_factory().subscribe(
        lambda x: x[rulename] == "test-non-muted-property" and x[processed] and _assert(
            x[rulename],
            True
        )
    )
    proc_events_rx_factory().subscribe(
        lambda x: x[rulename] == "test-muted-property" and x[processed] and _assert(
            x[rulename],
            False
        )
    )
    proc_events_rx_factory().subscribe(
        lambda x: x[rulename] == "test-direct-property" and x[processed] and _assert(
            x[rulename],
            True
        )
    )
    proc_events_rx_factory().subscribe(
        lambda x: x[rulename] == "test-muted-direct-property" and x[processed] and _assert(
            x[rulename],
            False
        )
    )
    proc_events_rx_factory().subscribe(
        lambda x: x[rulename] == "test-multi-set-properties-unmuted" and x[processed] and _assert(
            x[rulename],
            True
        )
    )
    proc_events_rx_factory().subscribe(
        lambda x: x[rulename] == "test-multi-set-properties-muted" and x[processed] and _assert(
            x[rulename],
            False
        )
    )

    router.route("test-set-subject-property", subject, {})

    assert subject.get("my_prop") == 11
    assert subject.get("dt_prop")[:10] == datetime.now().isoformat()[:10]
    assert subject.get_ext("my_ext_prop") == "extpropvalue"
    assert subject.get("my_prop_4") == -.5
    assert subject.get("my_silent_prop_5") == 5

    assert "test-set-subject-property" in asserted
    assert "test-non-muted-property" in asserted
    assert "test-muted-property" not in asserted
    assert "test-direct-property" in asserted
    assert "test-multi-set-properties-unmuted" in asserted