
import os

from dependency_injector import providers
from krules_core.providers import subject_storage,subject_storage_factory

from .storage_impl import SubjectsMongoStorage

subject_storage.override(
    providers.Factory(SubjectsMongoStorage)
)

mongodb_url = os.environ.get("TEST_MONGODB_SUBJECTS_STORAGE_URL", "mongodb://localhost:27017/admin")

subject_storage_factory.override(
    providers.Factory(
        lambda x: subject_storage(x, mongodb_url, os.environ.get("TEST_MONGODB_SUBJECTS_STORAGE_DATABASE", "test"),
                                  "test-subjects-atomic-ops",  use_atomic_ops_collection=True))
)
