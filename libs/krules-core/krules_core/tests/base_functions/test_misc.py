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
from krules_core import RuleConst
from krules_core.base_functions.misc import PyCall

from krules_core.core import RuleFactory

from krules_core.providers import (
    event_router_factory,
    proc_events_rx_factory,
    subject_factory,
    subject_storage_factory)

from .. import get_value_from_payload_diffs

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
    proc_events_rx_factory.override(providers.Singleton(rx_subject.ReplaySubject))

    return event_router_factory()


@pytest.fixture
def asserted():
    global asserted
    asserted = []
    return asserted


filters = RuleConst.FILTERS
processing = RuleConst.PROCESSING
rulename = RuleConst.RULENAME
passed = RuleConst.PASSED


def _assert(name, expr, msg="test failed"):
    global asserted
    assert expr, msg
    asserted.append(name)


def test_pycall(subject, router, asserted):

    def _func(in_value, raise_error, exc_to_raise=Exception("imbad")):

        if raise_error:
            raise exc_to_raise
        return in_value

    RuleFactory.create(
        "test-pycall-with-error",
        subscribe_to="test-pycall",
        data={
            processing: [
                PyCall(_func, ([1, 2], True),
                       on_success=lambda self: lambda x: x.reverse(),
                       on_error=lambda self: lambda x: self.payload.update({"got_errors": True}))
            ]
        }
    )

    RuleFactory.create(
        "test-pycall-no-error",
        subscribe_to="test-pycall",
        data={
            processing: [
                PyCall(_func, ([1, 2],), kwargs={"raise_error": False},
                       on_success=lambda self: lambda x: (
                           x.reverse(),
                           self.payload.update({"got_errors": False})
                       ))
            ]
        }
    )

    proc_events_rx_factory().subscribe(
        lambda x: x[rulename] == "test-pycall-no-error" and _assert(
            x[rulename],
            get_value_from_payload_diffs("pycall_returns", x[processing][0]["payload_diffs"], default_value=None) == [2, 1]
            and not get_value_from_payload_diffs("got_errors", x[processing][0]["payload_diffs"], default_value=False)
        )
    )

    proc_events_rx_factory().subscribe(
        lambda x: x[rulename] == "test-pycall-with-error" and _assert(
            x[rulename],
            not get_value_from_payload_diffs("pycall_returns", x[processing][0]["payload_diffs"], default_value=None) and
            get_value_from_payload_diffs("got_errors", x[processing][0]["payload_diffs"], default_value=False)
        )
    )

    router.route("test-pycall", subject, {})

    assert "test-pycall-no-error" in asserted
    assert "test-pycall-with-error" in asserted