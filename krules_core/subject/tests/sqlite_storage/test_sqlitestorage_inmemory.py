

from dependency_injector import providers as providers

from krules_core.subject.tests.sqlite_storage import SQLLiteSubjectStorage

from krules_core.providers import subject_storage, subject_storage_factory

#subject_storage = providers.Factory(SQLLiteSubjectStorage)


def test_memorydatabase():

    subject_storage_factory.override(
        providers.Factory(lambda x: subject_storage(":memory:", x))
    )

