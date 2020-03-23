
import rx

from dependency_injector import providers
from krules_core.providers import message_router_factory, results_rx_factory

from krules_core.core import RuleFactory
from krules_core import RuleConst

from datetime import datetime
import logging


def _assert(expr, msg="test failed"):
    assert expr, msg
    return True



# TODO: write tests for dispatch policy

def test_router():
    subject = "test-subject"
    results_rx_factory.override(providers.Singleton(rx.subjects.ReplaySubject))
    results_rx = results_rx_factory()

    start_time = datetime.now()
    router = message_router_factory()
    router.unregister_all()

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

    assert router.unregister_all() == 1, "Expected 1 element"
