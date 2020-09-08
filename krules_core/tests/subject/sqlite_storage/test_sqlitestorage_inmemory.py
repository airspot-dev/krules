

from dependency_injector import providers as providers

from krules_core.providers import subject_storage_factory
from krules_core.tests.subject.sqlite_storage import SQLLiteSubjectStorage


def test_memorydatabase():

    subject_storage_factory.override(
        providers.Factory(lambda x, **kwargs: SQLLiteSubjectStorage(x, ":memory:"))
    )
    assert not subject_storage_factory("test-subject").is_persistent()
    assert not subject_storage_factory("test-subject").is_concurrency_safe()

