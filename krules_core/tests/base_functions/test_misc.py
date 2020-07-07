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
    OnSubjectPropertyChanged, SetSubjectExtendedProperty, SetSubjectPropertySilently, StoreSubjectProperty, \
    RuleFunctionBase, StoreSubjectPropertySilently, SetSubjectProperties, IncrementSubjectProperty, \
    DecrementSubjectProperty, IncrementSubjectPropertySilently, DecrementSubjectPropertySilently
from krules_core.base_functions.misc import PyCall

from krules_core.core import RuleFactory

from krules_core.providers import (
    message_router_factory,
    results_rx_factory,
    subject_factory,
    subject_storage_factory)

<<<<<<< HEAD
from .. import get_value_from_payload_diffs

=======
>>>>>>> 30e47a7d0c47c64d0dc75ce776423c0170f9da82
counter = 0
asserted = []


@pytest.fixture
def subject():
    global counter
    counter += 1

    return subject_factory('test-subject-{0}'.format(counter)).flush()


@pytest.fixture
def router():
    router = message_router_factory()
    router.unregister_all()
    results_rx_factory.override(providers.Singleton(rx.subjects.ReplaySubject))

    return message_router_factory()


@pytest.fixture
def asserted():
    global asserted
    asserted = []
    return asserted


filters = RuleConst.FILTERS
processing = RuleConst.PROCESSING
rule_name = RuleConst.RULE_NAME
processed = RuleConst.PROCESSED


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
        ruledata={
            processing: [
                PyCall(_func, ([1, 2], True),
                       on_success=lambda self, x: x.reverse(),
<<<<<<< HEAD
                       on_error=lambda self, x: self.payload.update({"got_errors": True}))
=======
                       on_error=lambda self, x: self.payload.update({"got_error": True}))
>>>>>>> 30e47a7d0c47c64d0dc75ce776423c0170f9da82
            ]
        }
    )

    RuleFactory.create(
        "test-pycall-no-error",
        subscribe_to="test-pycall",
        ruledata={
            processing: [
                PyCall(_func, ([1, 2],), kwargs={"raise_error": False},
                       on_success=lambda self, x: (
                           x.reverse(),
<<<<<<< HEAD
                           self.payload.update({"got_errors": False})
=======
                           self.payload.update({"got_error": False})
>>>>>>> 30e47a7d0c47c64d0dc75ce776423c0170f9da82
                       ))
            ]
        }
    )

    results_rx_factory().subscribe(
        lambda x: x[rule_name] == "test-pycall-no-error" and _assert(
            x[rule_name],
<<<<<<< HEAD
            get_value_from_payload_diffs("pycall_returns", x[processing][0]["payload"], default_value=None) == [2, 1]
            and not get_value_from_payload_diffs("got_errors", x[processing][0]["payload"], default_value=False)
=======
            x[processing][0]["payload"]["pycall_returns"] == [2, 1] and
            not x[processing][0]["payload"]["got_error"]
>>>>>>> 30e47a7d0c47c64d0dc75ce776423c0170f9da82
        )
    )

    results_rx_factory().subscribe(
        lambda x: x[rule_name] == "test-pycall-with-error" and _assert(
            x[rule_name],
<<<<<<< HEAD
            not get_value_from_payload_diffs("pycall_returns", x[processing][0]["payload"], default_value=None) and
            get_value_from_payload_diffs("got_errors", x[processing][0]["payload"], default_value=False)
=======
            "pycall_returns" not in x[processing][0]["payload"] and
            x[processing][0]["payload"]["got_error"]
>>>>>>> 30e47a7d0c47c64d0dc75ce776423c0170f9da82
        )
    )

    router.route("test-pycall", subject, {})

<<<<<<< HEAD
    print(asserted)
=======
>>>>>>> 30e47a7d0c47c64d0dc75ce776423c0170f9da82
    assert "test-pycall-no-error" in asserted
    assert "test-pycall-with-error" in asserted
