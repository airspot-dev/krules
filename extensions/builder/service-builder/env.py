from dependency_injector import providers as providers
from krules_core.providers import (
    subject_storage_factory,
    configs_factory
)


def init():
    # Redis subjects storage support
    from redis_subjects_storage import storage_impl as redis_storage_impl

    subjects_redis_storage_settings = configs_factory() \
        .get("subjects-backends") \
        .get("redis")

    subject_storage_factory.override(
        providers.Factory(lambda name, **kwargs:
                              redis_storage_impl.SubjectsRedisStorage(
                                  name,
                                  subjects_redis_storage_settings.get("url"),
                                  key_prefix=subjects_redis_storage_settings.get("key_prefix")
                              )
                          )
    )
