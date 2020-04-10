
import os

from dependency_injector import providers
from krules_core.providers import subject_storage,subject_storage_factory

from .storage_impl import SubjectsMongoStorage

subject_storage.override(
    providers.Factory(SubjectsMongoStorage)
)

mongodb_url = os.environ.get("TEST_MONGODB_SUBJECTS_STORAGE_URL", "mongodb://localhost:27017/admin")
database = os.environ.get("TEST_MONGODB_SUBJECTS_STORAGE_DATABASE", "test")

subject_storage_factory.override(
    providers.Factory(
        lambda x: subject_storage(x, database, "test-subjects-atomic-ops", client_args=(mongodb_url,),
                                  use_atomic_ops_collection=False))
)
