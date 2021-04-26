from krules_core.subject import SubjectProperty, SubjectExtProperty

from krules_core.providers import subject_factory, subject_storage_factory
from dependency_injector import providers as providers
from krules_core.subject.empty_storage import EmptySubjectStorage


def setup_module(_):

    subject_storage_factory.override(
        providers.Factory(
            lambda *args, **kwargs:
                EmptySubjectStorage()
        )
    )


def teardown_module(_):
    subject_storage_factory.reset_last_overriding()


def test_load_store_and_flush():

    storage = subject_storage_factory("empty")

    storage.store(
        inserts=(
            SubjectProperty("p1", 1),
            SubjectProperty("p2", "2'3"),
            SubjectExtProperty("px1", 3),
            SubjectExtProperty("p1", "s1")
        )
    )

    props, ext_props = storage.load()

    assert len(props) == 0
    assert len(ext_props) == 0

    storage.store(
        updates=(
            SubjectProperty("p2", 3),
            SubjectExtProperty("p1", "s2"),
        ),
        deletes=(
            SubjectProperty("p1"),
            SubjectExtProperty("px1"),
        )
    )

    props, ext_props = storage.load()

    assert len(props) == 0
    assert len(ext_props) == 0

    storage.flush()

    assert len(props) == 0
    assert len(ext_props) == 0


def test_set_and_get():

    storage = subject_storage_factory("empty")
    storage.flush()

    assert storage.get("my_prop") is None

    new_value, old_value = storage.set(SubjectProperty("my_prop", 1))
    assert old_value is None
    assert new_value is None
    assert storage.get(SubjectProperty("my_prop")) is None

    storage.delete(SubjectProperty("my_prop"))
    new_value, old_value = storage.set(SubjectProperty("pset", 1), 0)
    assert old_value is None
    assert new_value is None
    new_value, old_value = storage.set(SubjectProperty("pset", "1'2"))
    assert new_value is None
    assert old_value is None
    assert storage.get(SubjectProperty("pset")) is None


def test_ext_props():

    storage = subject_storage_factory("test")

    storage.flush()

    storage.set(SubjectProperty("p1", 1))
    storage.set(SubjectProperty("p2", 2))
    storage.set(SubjectExtProperty("p3", 3))
    storage.set(SubjectExtProperty("p4", 4))

    props = storage.get_ext_props()

    assert len(props) == 0
