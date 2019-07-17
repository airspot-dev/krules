import responses
from dependency_injector import providers

from krules_core.providers import (
    settings_factory,
    message_router_factory,
    message_dispatcher_factory
)
from krules_core.route.router import MessageRouter
from .route.dispatcher import CloudEventsDispatcher

settings_factory.override(
    providers.Singleton(lambda: {})
)
message_router_factory.override(
    providers.Singleton(MessageRouter)
)
message_dispatcher_factory.override(
    providers.Singleton(lambda: CloudEventsDispatcher("http://localhost:9999"))
)

@responses.activate
def test_dispatcher():

    responses.add(responses.POST, "http://localhost:9999", status=200)

    router = message_router_factory()
    router.route("test-message", "test-subject", {})

    assert len(responses.calls) == 1


