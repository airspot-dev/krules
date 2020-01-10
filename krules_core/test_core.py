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

import dependency_injector.providers as providers

from .route.dispatcher import BaseDispatcher

from .route.router import MessageRouter
from .core import RuleFactory

from . import RuleConst

from .providers import (
    message_router_factory,
    results_rx_factory,
    subject_factory, settings_factory,
    message_dispatcher_factory
)

from datetime import datetime
import logging

def _assert(expr, msg="test failed"):
    assert expr, msg
    return True


counter = 0

settings_factory.override(
    providers.Singleton(lambda: {})
)

@pytest.fixture
def subject():
    from .subject.tests.mocksubject import MockSubject
    global counter
    counter += 1

    subject_factory.override(
        providers.Singleton(MockSubject)
    )
    return subject_factory('test-subject-{0}'.format(counter)).flush()

@pytest.fixture
def router():
    message_router_factory.override(
        providers.Singleton(lambda: MessageRouter(
            multiprocessing=True,
            wait_for_termination=True
        ))
    )
    return message_router_factory()


@pytest.fixture
def results_rx():
    results_rx_factory.override(providers.Singleton(rx.subjects.ReplaySubject))

    return results_rx_factory()


def test_router(subject, router, results_rx):

    start_time = datetime.now()
    RuleFactory.create('test-empty-rule',
                       subscribe_to="some-message",
                       ruledata={})

    results_rx.subscribe(
        lambda x: _assert(
                    x[RuleConst.MESSAGE] == "some-message" and
                    "key1" in x[RuleConst.PAYLOAD] and
                    x[RuleConst.PAYLOAD]["key1"] == "val1",
        )
    )
    router.route('some-message', subject, {"key1": "val1"})

    end_time = datetime.now()
    logging.getLogger().debug("######### {}".format(end_time-start_time))

    _assert(
        router.unregister_all() == 1,
        "Expected one rule to unregister"
    )


def test_filters(subject, router, results_rx):

    from .base_functions import Check
    from .base_functions import SetPayloadProperty

    RuleFactory.create('test-rule-filters-pass',
                       subscribe_to="test-message",
                       ruledata={
        RuleConst.FILTERS: [
            Check(True),
        ],
        RuleConst.PROCESSING: [
            SetPayloadProperty('processed', True),
        ],
    })

    RuleFactory.create('test-rule-filters-fails',
                       subscribe_to="test-message",
                       ruledata={
        RuleConst.FILTERS: [
            Check(False),
            Check(True),
        ],
        RuleConst.PROCESSING: [
            SetPayloadProperty('processed', False),  # never reached
        ],
    })

    results_rx.subscribe(
        lambda x: x[RuleConst.RULE_NAME] == 'test-rule-filters-pass' and
        _assert(
            x[RuleConst.PROCESSED] and
            len(x[RuleConst.PROCESSING]) == 1
        )
    )
    results_rx.subscribe(
        lambda x: x[RuleConst.RULE_NAME] == 'test-rule-filters-fails' and
        _assert(
            not x[RuleConst.PROCESSED] and
            len(x[RuleConst.PROCESSING]) == 0
        )
    )

    router.route("test-message", subject, {})


def test_with_payload(subject, router, results_rx):

    from .base_functions import SetPayloadProperty
    from .base_functions import with_payload

    RuleFactory.create('test-rule-copy-payload-data',
                           subscribe_to='test-message',
                           ruledata={
            RuleConst.PROCESSING: [
                SetPayloadProperty('copy_of_data', with_payload(lambda x: x['data']))
            ]
        })


    results_rx.subscribe(
        lambda x: _assert(
            x[RuleConst.PROCESSING][0][RuleConst.PAYLOAD]['copy_of_data'] == 1
        )
    )

    router.route("test-message", subject, {'data':  1})


def test_dispatch(subject, router, results_rx):

    _dispatched_messages = []

    class _TestDispatcher(BaseDispatcher):

        def dispatch(self, message, subject, payload):

            _dispatched_messages.append((message, subject, payload))

    message_dispatcher_factory.override(
        providers.Singleton(lambda: _TestDispatcher())
    )

    router.route('test-unhandled-message', subject, {"data": 1})

    _message, _subject, _payload = _dispatched_messages.pop()
    _assert(
        _message == 'test-unhandled-message' and
        _subject.name == subject.name and
        _payload.get("data") == 1
    )

