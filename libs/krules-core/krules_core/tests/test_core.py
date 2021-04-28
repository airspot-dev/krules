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

import dependency_injector.providers as providers
from krules_core.base_functions import Callable

from krules_core.route.dispatcher import BaseDispatcher

from krules_core.core import RuleFactory

from krules_core import RuleConst

from krules_core.providers import (
    event_router_factory,
    proc_events_rx_factory,
    subject_factory,
    event_dispatcher_factory
)


def _assert(expr, msg="test failed"):
    assert expr, msg
    return True


counter = 0


@pytest.fixture
def subject():
    global counter
    counter += 1

    return subject_factory('test-subject-{0}'.format(counter)).flush()


@pytest.fixture
def router():
    router = event_router_factory()
    router.unregister_all()
    proc_events_rx_factory.override(providers.Singleton(rx_subject.ReplaySubject))

    return event_router_factory()


def test_internal_routing(subject, router):
    RuleFactory.create('test-rule-filters-pass',
                       subscribe_to="test-type",
                       data={
                           RuleConst.FILTERS: [
                               Callable(
                                   lambda self: True
                               ),
                           ],
                           RuleConst.PROCESSING: [
                               Callable(
                                   lambda self:
                                   self.payload.setdefault(RuleConst.PASSED, True)
                               ),
                           ],
                       })

    RuleFactory.create('test-rule-filters-fails',
                       subscribe_to="test-type",
                       data={
                           RuleConst.FILTERS: [
                               Callable(lambda self: False),
                               Callable(lambda self: True),
                           ],
                           RuleConst.PROCESSING: [
                               Callable(
                                   lambda self:
                                   self.payload.setdefault(RuleConst.PASSED, False)
                               ),
                           ],
                       })

    proc_events_rx_factory().subscribe(
        lambda x: x[RuleConst.RULENAME] == 'test-rule-filters-pass' and
                  _assert(
                      x[RuleConst.PASSED] and
                      len(x[RuleConst.PROCESSING]) > 0 or print("##### LEN ", x[RuleConst.PROCESSING])
                  )
    )
    proc_events_rx_factory().subscribe(
        lambda x: x[RuleConst.RULENAME] == 'test-rule-filters-fails' and
                  _assert(
                      not x[RuleConst.PASSED] and
                      len(x[RuleConst.PROCESSING]) == 0
                  )
    )

    router.route("test-type", subject, {})


def test_dispatch(subject, router):
    _dispatched_events = []

    class _TestDispatcher(BaseDispatcher):

        def dispatch(self, event_type, subject, payload, **extra):
            _dispatched_events.append((event_type, subject, payload))

    event_dispatcher_factory.override(
        providers.Singleton(lambda: _TestDispatcher())
    )

    router.route('test-unhandled-event', subject, {"data": 1})

    t, subject, payload = _dispatched_events.pop()
    _assert(
        t == 'test-unhandled-event' and
        subject.name == subject.name and
        payload.get("data") == 1
    )
