# Copyright 2019 The KRules Authors
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# TODO: This file is a replica of the test_storage.py file in the krules-core module. Implement a strategy
# to have a generic test for the storage component outside the module that implements it

import json
import os

import pytest

import time
from multiprocessing import Process

from krules_core.providers import subject_storage_factory
from krules_core.subject import SubjectProperty, SubjectExtProperty, PropertyType

from dependency_injector import providers as providers

from redis_subjects_storage import storage_impl

subject_storage = providers.Factory(storage_impl.SubjectsRedisStorage)


def setup_module(_):
    redis_url = os.environ.get("TEST_REDIS_SUBJECTS_STORAGE_URL", "redis://localhost/0")

    subject_storage_factory.override(
        providers.Factory(lambda x: subject_storage(x, redis_url, "myapp"))
    )


def teardown_module(_):
    subject_storage_factory.reset_last_overriding()

@pytest.fixture
def storage_subject1():
    return subject_storage_factory("subject1").flush()


@pytest.fixture
def storage_subject2():
    return subject_storage_factory("subject2").flush()


def test_factories(storage_subject1, storage_subject2):

    assert str(storage_subject1) != str(storage_subject2)

    assert str(subject_storage_factory("subject1")) == str(storage_subject1)


# def test_property_kinds():
#
#     prop_p = SubjectProperty("p")
#     assert prop_p.value is None
#     assert prop_p.type == PropertyType.DEFAULT
#     prop_e = SubjectExtProperty("p")
#     assert prop_e.type == PropertyType.EXTENDED
#
#     # test simple value
#     prop = SubjectProperty("p", 1)
#     assert prop.json_value() == json.dumps(1)
#     assert prop.get_value() == 1
#     prop = SubjectExtProperty("p", 2)
#     assert prop.get_value() == 2
#     assert prop.json_value() == json.dumps(2)
#
#     # callable no args
#     prop = SubjectProperty("p", lambda: 10)
#     assert prop.json_value() == json.dumps(10)
#     assert prop.get_value() == 10
#     # callable with args
#     prop = SubjectProperty("p", lambda x: x*2)
#     assert prop.json_value(2) == json.dumps(4)
#     assert prop.get_value() == 4
#     prop = SubjectExtProperty("p", lambda x: x.format(2))
#     assert prop.get_value("value is {}") == "value is 2"
#     assert prop.json_value("value is {}") == json.dumps("value is 2")


def test_load_store_and_flush(storage_subject1):

    props, ext_props = storage_subject1.load()

    assert props == {} and ext_props == {}

    storage_subject1.store(
        inserts=(
            SubjectProperty("p1", 1),
            SubjectProperty("p2", "2'3"),  # sql needs escape
            SubjectExtProperty("px1", 3),
            SubjectExtProperty("p1", "s1")
        )
    )

    props, ext_props = storage_subject1.load()

    assert len(props) == 2
    assert len(ext_props) == 2
    assert props["p1"] == 1
    assert props["p2"] == "2'3"
    assert ext_props["px1"] == 3
    assert ext_props["p1"] == "s1"

    storage_subject1.store(
        updates=(
            SubjectProperty("p2", 3),
            SubjectExtProperty("p1", "s2"),
        ),
        deletes=(
            SubjectProperty("p1"),
            SubjectExtProperty("px1"),
        )
    )

    props, ext_props = storage_subject1.load()

    assert len(props) == 1
    assert len(ext_props) == 1
    assert props["p2"] == 3
    assert ext_props["p1"] == "s2"

    storage_subject1.flush()

    props, ext_props = storage_subject1.load()

    assert props == {} and ext_props == {}


def test_multiple_subjects(storage_subject1, storage_subject2):

    storage_subject1.store(
        inserts=(
            SubjectProperty("p1", 1),
            SubjectProperty("p2", 2),
            SubjectExtProperty("p3", 3),
        )
    )
    storage_subject2.store(
        inserts=(
            SubjectProperty("p1", 1),
            SubjectExtProperty("p2", 2),
        )
    )

    props1, ext_props1 = storage_subject1.load()
    props2, ext_props2 = storage_subject2.load()

    assert len(props1) == 2
    assert len(ext_props1) == 1
    assert len(props2) == 1
    assert len(ext_props2) == 1

    storage_subject1.store(
        updates=(
            SubjectProperty("p1", 10),
            SubjectExtProperty("p3", 30)
        ),
        deletes=(
            SubjectProperty("p2"),
        )
    )

    props1, ext_props1 = storage_subject1.load()
    props2, ext_props2 = storage_subject2.load()

    assert len(props1) == 1
    assert len(props2) == 1
    assert len(ext_props2) == 1

    assert props1["p1"] == 10
    assert props2["p1"] == 1


def test_set_and_get(storage_subject1):

    with pytest.raises(AttributeError):
        storage_subject1.get(SubjectProperty("pset"))

    # simple value
    new_value, old_value = storage_subject1.set(SubjectProperty("pset", 1))
    assert old_value is None
    assert new_value == 1
    storage_subject1.delete(SubjectProperty("pset"))
    new_value, old_value = storage_subject1.set(SubjectProperty("pset", 1), 0)
    assert old_value == 0
    assert new_value == 1
    new_value, old_value = storage_subject1.set(SubjectProperty("pset", "1'2"))
    assert new_value == "1'2"
    assert old_value == 1

    assert storage_subject1.get(SubjectProperty("pset")) == "1'2"

    # computed value
    storage_subject1.set(SubjectProperty("pset", lambda: "1'2"))  # no args
    storage_subject1.set(SubjectProperty("pset", lambda x: x.replace("'", "$")))

    assert storage_subject1.get(SubjectProperty("pset")) == "1$2"

    # having exceptions in writing operations does not cause bad status (eg; write-locked database)
    with pytest.raises(Exception):
        storage_subject1.set(SubjectProperty("pset", lambda x: x/0))
    storage_subject1.set(SubjectProperty("psetX", 0))

    # test concurrency
    if storage_subject1.is_concurrency_safe():
        def _wait_and_incr(val):
            time.sleep(1)
            return val+1

        def _call_wait_and_incr():
            storage_subject1.set(SubjectProperty("psetX", _wait_and_incr))
        p = Process(target=_call_wait_and_incr)
        p.start()
        storage_subject1.set(SubjectProperty("psetX", lambda x: x+1))
        p.join()
        assert storage_subject1.get(SubjectProperty("psetX")) == 2


def test_ext_props(storage_subject1, storage_subject2):
    storage_subject1.flush()
    storage_subject2.flush()

    storage_subject1.set(SubjectProperty("p1", 1))
    storage_subject1.set(SubjectProperty("p2", 2))
    storage_subject1.set(SubjectExtProperty("p3", 3))
    storage_subject1.set(SubjectExtProperty("p4", 4))
    storage_subject2.set(SubjectExtProperty("p5", 5))

    props = storage_subject1.get_ext_props()
    assert len(props) == 2

    assert "p3" in props and props["p3"] == 3
    assert "p4" in props and props["p4"] == 4


def test_ret_values(storage_subject1):

    storage_subject1.flush()

    vp1 = 1

    new_val, old_val = storage_subject1.set(SubjectProperty("p1", vp1))

    assert new_val == vp1
    assert old_val is None

    new_val, old_val = storage_subject1.set(SubjectProperty("p1", lambda v: v+1))

    assert old_val == vp1
    assert new_val == vp1+1




