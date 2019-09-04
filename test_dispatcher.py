from pytest_localserver import http, plugin

from dependency_injector import providers

from krules_core.providers import (
    settings_factory,
    message_router_factory,
    message_dispatcher_factory
)
from krules_core.route.router import MessageRouter
from .route.dispatcher import CloudEventsDispatcher

httpserver = plugin.httpserver


settings_factory.override(
    providers.Singleton(lambda: {})
)
message_router_factory.override(
    providers.Singleton(MessageRouter)
)


def test_dispatched_event(httpserver):

    # TODO: replaced requests with pycurl..
    #responses.add(responses.POST, "http://localhost:9999", status=200)
    message_dispatcher_factory.override(
        providers.Singleton(lambda: CloudEventsDispatcher(httpserver.url))
    )
    router = message_router_factory()
    event = router.route("test-message", "test-subject", {"key1": "hello"})
    assert event.Data()["key1"] == "hello"
    #extensions = event.Extensions()["extension"]
    extensions = event.Extensions()
    assert extensions["subject"] == "test-subject"
    assert extensions["origin_id"] == event.EventID()



