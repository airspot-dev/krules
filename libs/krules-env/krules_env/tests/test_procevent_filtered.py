import pytest
import os
from rx import subject as rx_subject
from krules_env import RULE_PROC_EVENT, publish_proc_events_filtered
from krules_core.providers import proc_events_rx_factory, subject_factory, event_router_factory

from dependency_injector import providers
from krules_core.base_functions.filters import Filter
from krules_core.base_functions.processing import Process, SetPayloadProperty

from krules_core import RuleConst, ProcEventsLevel

from krules_core.core import RuleFactory

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


filters = RuleConst.FILTERS
processing = RuleConst.PROCESSING
rulename = RuleConst.RULENAME
processed = RuleConst.PASSED
subscribed_rules = []


def test_filtered(router, subject):
    os.environ["PUBLISH_PROCEVENTS_LEVEL"] = str(ProcEventsLevel.FULL)
    os.environ["PUBLISH_PROCEVENTS_MATCHING"] = "passed=true"

    proc_events_rx_factory().subscribe(
        on_next=lambda x: publish_proc_events_filtered(x, "passed=true", lambda match: match is not None,
                                                       debug=True))

    RuleFactory.create('check-even-value',
                       subscribe_to="event-test-procevents",
                       data={
                           filters: [
                               Filter(lambda payload: payload["value"] % 2 == 0),
                           ],
                           processing: [
                               SetPayloadProperty("isEven", True),
                           ]
                       })

    RuleFactory.create('check-odd-value',
                       subscribe_to="event-test-procevents",
                       data={
                           filters: [
                               Filter(lambda payload: payload["value"] % 2 != 0),
                           ],
                           processing: [
                               SetPayloadProperty("isEven", False),
                           ]
                       })

    RuleFactory.create('test-procevents-filter',
                       subscribe_to=RULE_PROC_EVENT,
                       data={
                           processing: [
                               Process(lambda payload: subscribed_rules.append(payload["name"])),
                           ],
                       })

    router.route("event-test-procevents", subject, {"value": 2})

    assert "check-even-value" in subscribed_rules
    assert "check-odd-value" not in subscribed_rules
