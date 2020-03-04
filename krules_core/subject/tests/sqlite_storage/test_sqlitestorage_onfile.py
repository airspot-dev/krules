

import os

TEST_FNAME="subjectstore_test.sqlite"


from dependency_injector import providers as providers

from krules_core.subject.tests.sqlite_storage import SQLLiteSubjectStorage

from krules_core.providers import subject_storage, subject_storage_factory

subject_storage = providers.Factory(SQLLiteSubjectStorage)


def test_memorydatabase():

    if os.path.exists(TEST_FNAME):
        os.unlink(TEST_FNAME)

    subject_storage_factory.override(
        providers.Factory(lambda x: subject_storage(TEST_FNAME, x))
    )
    assert subject_storage_factory("test-subject").is_persistent()
    assert subject_storage_factory("test-subject").is_concurrency_safe()



