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
import re

import pytest
import rx
from dependency_injector import providers
from krules_core.base_functions.filters import Returns, CheckSubjectProperty, PayloadMatch, SubjectNameMatch, \
    SubjectNameDoesNotMatch, IsTrue, IsFalse, PayloadMatchOne, SubjectPropertyChanged

from krules_core import RuleConst

from krules_core.core import RuleFactory

from krules_core.providers import (
    event_router_factory,
    proc_events_rx_factory,
    subject_factory,
)

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


def test_return(subject, router, asserted):

    RuleFactory.create('test-returns',
                       subscribe_to="event-test-returns",
                       data={
                           filters: [
                               Returns("something"),
                           ],
                       })

    proc_events_rx_factory().subscribe(
        lambda x: x[rulename] == 'test-returns' and _assert(
            'test-returns-something',
            x[processed] and x[filters][0]["returns"] == "something"
            )

    )

    router.route("event-test-returns", subject, {})

    assert 'test-returns-something' in asserted


def test_truth(subject, router, asserted):

    RuleFactory.create('test-is-true',
                       subscribe_to="event-test-truth",
                       data={
                           filters: [
                               IsTrue(
                                    lambda payload: payload["it-works"]
                               ),
                           ],
                       })

    RuleFactory.create('test-is-false',
                       subscribe_to="event-test-truth",
                       data={
                           filters: [
                               IsFalse(
                                   lambda payload: payload["it-works"] is False
                               ),
                           ],
                       })

    proc_events_rx_factory().subscribe(
        lambda x: x[rulename] == 'test-is-true' and _assert(
            'test-is-true',
            x[processed] and x[filters][0]["returns"] is True
            )
    )
    proc_events_rx_factory().subscribe(
        lambda x: x[rulename] == 'test-is-false' and _assert(
            'test-is-false',
            x[processed] and x[filters][0]["returns"] is True
            )

    )

    router.route("event-test-truth", subject, {'it-works': True})

    assert 'test-is-true' in asserted
    assert 'test-is-false' in asserted


def test_subject_match(router, asserted):

    user_subject = "user|000001"

    RuleFactory.create('test-subject-match',
                       subscribe_to='event-user-action',
                       data={
                           filters: [
                               SubjectNameMatch(r"^user\|(?P<user_id>.+)", payload_dest="user_info"),
                               IsTrue(
                                   lambda payload: "user_id" in payload.get("user_info", {})
                               )
                           ]
                       })

    RuleFactory.create('test-subject-does-not-match',
                       subscribe_to='event-user-action',
                       data={
                           filters: [
                               SubjectNameDoesNotMatch(r"^device\|(?P<device_id>.+)", payload_dest="device_info"),
                           ]
                       })

    proc_events_rx_factory().subscribe(
        lambda x: x[rulename] == 'test-subject-match' and _assert(
            'test-subject-match',
            x[processed] is True
            )
    )
    proc_events_rx_factory().subscribe(
        lambda x: x[rulename] == 'test-subject-does-not-match' and _assert(
            'test-subject-does-not-match',
            x[processed] is True
            )
    )

    router.route("event-user-action", user_subject, {})

    assert 'test-subject-match' in asserted
    assert 'test-subject-does-not-match' in asserted


def test_check_subject_property(router, subject, asserted):

    RuleFactory.create(
        "test-simple-subject-property",
        subscribe_to="test-subject-property",
        data={
            filters: [
                CheckSubjectProperty("prop-1", "value-1"),
                CheckSubjectProperty("prop-2", 2),
            ]
        }
    )

    RuleFactory.create(
        "test-simple-subject-property-fails",
        subscribe_to="test-subject-property",
        data={
            filters: [
                CheckSubjectProperty("prop-1", "value-1"),
                CheckSubjectProperty("prop-2", "2"),
            ]
        }
    )

    import re
    RuleFactory.create(
        "test-expr-subject-property",
        subscribe_to="test-subject-property",
        data={
            filters: [
                # one argument (value)
                CheckSubjectProperty("prop-1"),
                CheckSubjectProperty("prop-1", lambda v: v in ("value-1",) and re.match("value-[0-9]", v)),
                CheckSubjectProperty("prop-2", lambda v: type(v) is int),
                CheckSubjectProperty("ext-prop", extended=True)
            ]
        }
    )

    subject.set("prop-1", "value-1")
    subject.set("prop-2", 2)
    subject.set_ext("ext-prop-2", "extprop")

    proc_events_rx_factory().subscribe(
        lambda x: x[rulename] == "test-simple-subject-property" and _assert(
            x[rulename],
            x[processed] is True
        )
    )
    proc_events_rx_factory().subscribe(
        lambda x: x[rulename] == "test-simple-subject-property-fails" and _assert(
            x[rulename],
            x[processed] is False
        )
    )

    router.route("test-subject-property", subject, {})

    assert "test-simple-subject-property" in asserted
    assert "test-simple-subject-property-fails" in asserted

    # clean up
    router.unregister_all()
    proc_events_rx_factory.override(providers.Singleton(rx.subjects.ReplaySubject))

    # check direct
    subject.set("prop-1", "value-2")
    subject.set_ext("ext-prop-3", 1)

    # properties are not yet stored, rules should fail
    RuleFactory.create(
        "test-subject-property-direct",
        subscribe_to="test-subject-property-direct",
        data={
            filters: [
                CheckSubjectProperty("v-prop-1", "value-2", cached=False),  # prop-1 is still value-1
            ]
        }
    )

    RuleFactory.create(
        "test-subject-property-ext-direct",
        subscribe_to="test-subject-property-direct",
        data={
            filters: [
                CheckSubjectProperty("ext-prop-3", cached=False),  # ext-prop-3 does not exists yet
            ]
        }
    )

    proc_events_rx_factory().subscribe(
        lambda x: x[rulename] == "test-subject-property-direct" and _assert(
            x[rulename],
            not x[processed]
        )
    )

    proc_events_rx_factory().subscribe(
        lambda x: x[rulename] == "test-subject-property-ext-direct" and _assert(
            x[rulename],
            not x[processed]
        )
    )

    router.route("test-subject-property-direct", subject, {})

    assert "test-subject-property-direct" in asserted
    assert "test-subject-property-ext-direct" in asserted


def test_check_payload_match(router, subject, asserted):

    payload = {
        "batch_data": [
          {
            "time": "2020-03-10T17:16:16.014673",
            "value": 100
          },
          {
            "time": "2020-03-10T17:21:16.014673",
            "value": 50
          },
          {
            "time": "2020-03-10T17:26:16.014673",
            "value": 60
          },
          {
            "time": "2020-03-10T17:31:16.014673",
            "value": 105
          },
          {
            "time": "2020-03-10T17:36:16.014673",
            "value": 120
          }
        ],
        "device_info": {
            "id": "0AFB1110",
            "disabled": False,
        }
      }

    # just check no empty
    RuleFactory.create(
        "test-check-payload-jpmatch-not-empty",
        subscribe_to="test-check-payload-jpmatch",
        data={
            filters: [
                PayloadMatch("$..batch_data[?@.value>100]")  # returns two elements - pass
            ]
        }
    )
    # store result
    RuleFactory.create(
        "test-check-payload-jpmatch-store-result",
        subscribe_to="test-check-payload-jpmatch",
        data={
            filters: [
                PayloadMatch("$.batch_data[?@.value>100]", lambda m: len(m) == 2),
                PayloadMatch("$.batch_data[?@.value>100]", payload_dest="jpexpr_match"),
                IsTrue(
                    lambda payload: len(payload['jpexpr_match']) == 2
                )
            ]
        }
    )
    # match one
    RuleFactory.create(
        "test-check-payload-jpmatch-one",
        subscribe_to="test-check-payload-jpmatch",
        data={
            filters: [
                PayloadMatchOne("$.device_info.id", "0AFB1110"),
                PayloadMatchOne("$.device_info.id", payload_dest="device_id"),
                PayloadMatchOne("$.device.info.disabled", lambda disabled: not disabled),
                IsTrue(
                    lambda payload: payload["device_id"] == "0AFB1110"
                )
            ]
        }
    )

    proc_events_rx_factory().subscribe(
        lambda x: x[rulename] == "test-check-payload-jpmatch-not-empty" and _assert(
            x[rulename],
            x[processed]
        )
    )
    proc_events_rx_factory().subscribe(
        lambda x: x[rulename] == "test-check-payload-jpmatch-store-result" and _assert(
            x[rulename],
            x[processed]
        )
    )
    proc_events_rx_factory().subscribe(
        lambda x: x[rulename] == "test-check-payload-jpmatch-one" and _assert(
            x[rulename],
            x[processed]
            and x[filters][0]["returns"] is True
            and x[filters][1]["returns"] is True
            and x[filters][2]["returns"] is True
        )
    )

    router.route("test-check-payload-jpmatch", subject, payload)

    assert "test-check-payload-jpmatch-not-empty" in asserted
    assert "test-check-payload-jpmatch-store-result" in asserted
    assert "test-check-payload-jpmatch-one" in asserted


def test_on_subject_property_changed(router, subject, asserted):

    from krules_core import types
    RuleFactory.create(
        "test-prop-changed",
        subscribe_to=types.SUBJECT_PROPERTY_CHANGED,
        data={
            filters: [
                SubjectPropertyChanged("prop_a"),
                SubjectPropertyChanged(lambda: "prop_{}".format("a")),
                SubjectPropertyChanged(lambda prop: re.match("prop_[a-z]", prop)),
                SubjectPropertyChanged("prop_a", lambda: 1),
                SubjectPropertyChanged("prop_a", value=lambda value: value > 0),
                SubjectPropertyChanged("prop_a", value=lambda value, old_value: value == 1 and old_value is None),
                SubjectPropertyChanged("prop_a", old_value=None),
                SubjectPropertyChanged("prop_a", old_value=lambda old_value: old_value is None)
           ]
        }
    )
    RuleFactory.create(
        "test-prop-changed-fails-1",
        subscribe_to=types.SUBJECT_PROPERTY_CHANGED,
        data={
            filters: [
                SubjectPropertyChanged("prop_b"),
           ]
        }
    )
    RuleFactory.create(
        "test-prop-changed-fails-2",
        subscribe_to=types.SUBJECT_PROPERTY_CHANGED,
        data={
            filters: [
                SubjectPropertyChanged("prop_a", lambda value: value > 1),
            ]
        }
    )
    RuleFactory.create(
        "test-prop-changed-fails-3",
        subscribe_to=types.SUBJECT_PROPERTY_CHANGED,
        data={
            filters: [
                SubjectPropertyChanged("prop_a", lambda value, old_value: value == 1 and old_value is not None),
            ]
        }
    )
    RuleFactory.create(
        "test-prop-changed-fails-4",
        subscribe_to=types.SUBJECT_PROPERTY_CHANGED,
        data={
            filters: [
                SubjectPropertyChanged("prop_a", lambda value, old_value: value == 1,
                                         lambda old_value: old_value is not None),
            ]
        }
    )

    proc_events_rx_factory().subscribe(
        lambda x: x[rulename] == "test-prop-changed" and _assert(
            x[rulename],
            x[processed], "{} not processed".format(x[rulename])
        )
    )
    proc_events_rx_factory().subscribe(
        lambda x: x[rulename] == "test-prop-changed-fails-1" and _assert(
            x[rulename],
            not x[processed], "{} should not be not processed".format(x[rulename])
        )
    )
    proc_events_rx_factory().subscribe(
        lambda x: x[rulename] == "test-prop-changed-fails-2" and _assert(
            x[rulename],
            not x[processed], "{} should not be not processed".format(x[rulename])
        )
    )
    proc_events_rx_factory().subscribe(
        lambda x: x[rulename] == "test-prop-changed-fails-3" and _assert(
            x[rulename],
            not x[processed], "{} should not be not processed".format(x[rulename])
        )
    )
    proc_events_rx_factory().subscribe(
        lambda x: x[rulename] == "test-prop-changed-fails-4" and _assert(
            x[rulename],
            not x[processed], "{} should not be not processed".format(x[rulename])
        )
    )


    subject.prop_a = 1

    assert 'test-prop-changed' in asserted
    assert 'test-prop-changed-fails-1' in asserted
    assert 'test-prop-changed-fails-2' in asserted
    assert 'test-prop-changed-fails-3' in asserted
    assert 'test-prop-changed-fails-4' in asserted



