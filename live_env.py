import responses
from dependency_injector import providers

from krules_core.providers import (
    subject_factory,
    settings_factory,
    message_router_factory,
    message_dispatcher_factory
)


from krules_core.route.router import MessageRouter
from .route.dispatcher import CloudEventsDispatcher

def init_redis(**kwargs):

    from subject_redis.core import SubjectRedis
    from subject_redis import ConfigKeyConst as SubjectRedisConfigConst

    rkey_prefix=kwargs.pop(SubjectRedisConfigConst.RKEY_PREFIX, "ktest_subject")

    settings_factory.override(
        providers.Singleton(lambda: {
            SubjectRedisConfigConst.RKEY_PREFIX: rkey_prefix,
            SubjectRedisConfigConst.CONNECT_KWARGS: kwargs
        })
    )
    subject_factory.override(
        providers.Factory(SubjectRedis)
    )


def init(address="http://localhost:9999", sub_env=init_redis):

    settings_factory.override(
        providers.Singleton(lambda: {})
    )
    message_router_factory.override(
        providers.Singleton(MessageRouter)
    )
    message_dispatcher_factory.override(
        providers.Singleton(lambda: CloudEventsDispatcher(address))
    )

    sub_env()

