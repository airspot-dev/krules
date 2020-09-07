

import os

from krules_core.tests.subject.sqlite_storage import SQLLiteSubjectStorage

TEST_FNAME="subjectstore_test.sqlite"


from dependency_injector import providers as providers

from krules_core.providers import subject_storage_factory


def test_memorydatabase():

    if os.path.exists(TEST_FNAME):
        os.unlink(TEST_FNAME)

    subject_storage_factory.override(
        providers.Factory(lambda x, **kwargs: SQLLiteSubjectStorage(x, TEST_FNAME))
    )
    assert subject_storage_factory("test-subject").is_persistent()
    assert subject_storage_factory("test-subject").is_concurrency_safe()



