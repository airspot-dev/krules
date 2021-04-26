from dependency_injector import providers as providers
from krules_core.providers import (
    subject_storage_factory,
    configs_factory
)


def init():
    pass  # remove me
    ## Redis subjects storage support
    # from redis_subjects_storage import storage_impl as redis_storage_impl
    #
    # subjects_redis_storage_settings = configs_factory() \
    #     .get("subjects-backends") \
    #     .get("redis")
    #
    # subject_storage_factory.override(
    #     providers.Factory(lambda name, **kwargs:
    #                           redis_storage_impl.SubjectsRedisStorage(
    #                               name,
    #                               subjects_redis_storage_settings.get("url"),
    #                               key_prefix=subjects_redis_storage_settings.get("key_prefix")
    #                           )
    #                       )
    # )

    ## MongoDB subjects storage support
    # from mongodb_subjects_storage import storage_impl as mongo_storage_impl
    #
    # subjects_mongodb_storage_settings = configs_factory() \
    #     .get("subjects-backends") \
    #     .get("mongodb")
    #
    # client_args = subjects_mongodb_storage_settings["client_args"]
    # client_kwargs = subjects_mongodb_storage_settings["client_kwargs"]
    # database = subjects_mongodb_storage_settings["database"]
    # collection = subjects_mongodb_storage_settings.get("collection", "subjects")
    #
    # subject_storage_factory.override(
    #     providers.Factory(
    #         lambda x, **kwargs: mongo_storage_impl.SubjectsMongoStorage(
    #             x,
    #             database,
    #             collection,
    #             client_args=client_args,
    #             client_kwargs=client_kwargs,
    #         ))
    # )
