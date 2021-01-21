from dependency_injector import providers as providers
from krules_core.providers import (
    subject_storage_factory,
    configs_factory
)
import os


def init():
    from k8s_subjects_storage import storage_impl as k8s_storage_impl
    from redis_subjects_storage import storage_impl as redis_storage_impl

    # Redis subjects storage support
    subjects_redis_storage_settings = configs_factory() \
        .get("subjects-backends") \
        .get("redis")

    subject_storage_factory.override(
        providers.Factory(lambda name, event_info, event_data:
                          name.startswith("k8s:") and k8s_storage_impl.SubjectsK8sStorage(
                              resource_path=name[4:],
                              resource_body=event_data and event_data.get("object", event_data) or None,
                          )
                          or redis_storage_impl.SubjectsRedisStorage(
                              name,
                              subjects_redis_storage_settings.get("url"),
                              key_prefix=subjects_redis_storage_settings.get("key_prefix")
                          )
                          )
    )
