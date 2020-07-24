
import rx

from dependency_injector import providers
from krules_core.providers import event_router_factory, proc_events_rx_factory

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
    proc_events_rx_factory.override(providers.Singleton(rx.subjects.ReplaySubject))
    proc_events_rx = proc_events_rx_factory()

    start_time = datetime.now()
    router = event_router_factory()
    router.unregister_all()

    RuleFactory.create('test-empty-rule',
                       subscribe_to="some-type",
                       data={})

    proc_events_rx.subscribe(
        lambda x: _assert(
                    x[RuleConst.TYPE] == "some-type" and
                    "key1" in x[RuleConst.PAYLOAD] and
                    x[RuleConst.PAYLOAD]["key1"] == "val1",
        )
    )
    router.route('some-type', subject, {"key1": "val1"})

    end_time = datetime.now()
    logging.getLogger().debug("######### {}".format(end_time-start_time))

    assert router.unregister_all() == 1, "Expected 1 element"
