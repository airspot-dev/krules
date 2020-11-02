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



import pytest
from dependency_injector import providers as providers


from krules_core.subject import PayloadConst, PropertyType

_test_events = []


class Router(object):

    def route(self, type, subject, payload):
        _test_events.append((type, subject, payload))


def setup_module(_):
    from dependency_injector import providers as providers
    from krules_core.providers import event_router_factory

    event_router_factory.override(
        providers.Singleton(Router)
    )


def teardown_module(_):
    from krules_core.providers import event_router_factory

    event_router_factory.reset_last_overriding()


counter = 0


# @pytest.fixture
# def messages():
#     from krules_core import ConfigKeyConst
#     from krules_core.providers import settings_factory
#     settings_factory.override(
#         providers.Singleton(
#             lambda: {
#                 ConfigKeyConst.MESSAGE_TOPICS_PREFIX: "tests-"
#             }
#         )
#     )
#     from krules_core import messages
#     return messages

def test_factory():

    from krules_core.providers import subject_factory
    test_subject = subject_factory("test-subject")
    assert test_subject.name == "test-subject"


@pytest.fixture
def subject():
    from krules_core.providers import subject_factory

    global counter
    counter += 1
    return subject_factory('test-subject-{0}'.format(counter)).flush()

@pytest.fixture
def subject_no_cache():
    from krules_core.providers import subject_factory

    global counter
    counter += 1
    return subject_factory('test-subject-{0}'.format(counter), use_cache_default=False).flush()


def test_set_get_del(subject):
    from krules_core.providers import subject_factory, subject_storage_factory

    subject.flush()

    # store nothing
    subject.store()

    global _test_events
    _test_events = []

    # USE CACHE (default)
    subject.set("my-prop", 1)
    assert subject.get("my-prop") == 1

    # not yet stored
    subject_copy = subject_factory(subject.name)
    with pytest.raises(AttributeError):
        subject_copy.get("my-prop")
    subject.store()
    subject_copy = subject_factory(subject.name)
    if subject_storage_factory(subject_copy.name).is_persistent():
        assert subject_copy.get("my-prop") == 1

    # callables
    new_value, old_value = subject.set("my-prop", lambda x: x+2)
    assert new_value == 3 and old_value == 1
    new_value, old_value = subject.set("my-prop-2", lambda x: x is None and 1 or x + 2)
    assert new_value == 1 and old_value is None

    # events
    assert len(_test_events) == 3
    from krules_core import types
    #   type
    assert _test_events[0][0] == _test_events[1][0] == _test_events[2][0] == types.SUBJECT_PROPERTY_CHANGED
    #   subject
    assert _test_events[0][1].name == _test_events[1][1].name == _test_events[2][1].name == subject.name
    #   payload
    payload = _test_events[0][2]
    assert payload[PayloadConst.PROPERTY_NAME] == "my-prop" and payload[PayloadConst.OLD_VALUE] is None \
        and payload[PayloadConst.VALUE] == 1
    payload = _test_events[1][2]
    assert payload[PayloadConst.PROPERTY_NAME] == "my-prop" and payload[PayloadConst.OLD_VALUE] == 1 \
        and payload[PayloadConst.VALUE] == 3
    payload = _test_events[2][2]
    assert payload[PayloadConst.PROPERTY_NAME] == "my-prop-2" and payload[PayloadConst.OLD_VALUE] is None \
        and payload[PayloadConst.VALUE] == 1

    # old the same with extended properties except that they are mute
    _test_events = []
    subject.set_ext("my-prop", 1)
    assert subject.get_ext("my-prop") == 1

    # not yet stored
    subject_copy = subject_factory(subject.name)
    with pytest.raises(AttributeError):
        subject_copy.get_ext("my-prop")
    subject.store()
    if subject_storage_factory(subject.name).is_persistent():
        subject_copy = subject_factory(subject.name)
        assert subject_copy.get_ext("my-prop") == 1

    # callables
    new_value, old_value = subject.set_ext("my-prop", lambda x: x+2)
    assert new_value == 3 and old_value == 1
    new_value, old_value = subject.set_ext("my-prop-2", lambda x: x is None and 1 or x + 2)
    assert new_value == 1 and old_value is None

    # events
    assert len(_test_events) == 0

    # muted
    val, _ = subject.set("my-prop", "silent", muted=True)
    assert val == "silent" and len(_test_events) == 0

    # NO CACHE
    subject.set("my-prop", 0, cached=False)  # not calling store
    if subject_storage_factory(subject.name).is_persistent():
        subject = subject_factory(subject.name)
        val = subject.get("my-prop", cached=False)
        assert val == 0
    #  with callables
    val, old_val = subject.set("my-prop", lambda x: x+5, cached=False)
    assert old_val == 0 and val == 5
    #  events produced
    assert len(_test_events) == 2

    # same with exts
    _test_events = []
    subject.set_ext("my-prop", 0, cached=False)  # not calling store
    if subject_storage_factory(subject.name).is_persistent():
        subject = subject_factory(subject.name)
        val = subject.get_ext("my-prop", cached=False)
        assert val == 0
    #  with callables
    val, old_val = subject.set_ext("my-prop", lambda x: x+5, cached=False)
    assert old_val == 0 and val == 5
    #  events NOT produced
    assert len(_test_events) == 0

    #  with cached
    if subject_storage_factory(subject.name).is_persistent():
        subject = subject_factory(subject.name)
        val = subject.get("my-prop")
        assert val == 5  # prop cached
        subject.set("my-prop", 1, cached=False)
        val = subject.get("my-prop")  # from cache
        assert val == 1
        subject.store()
        #  update cache
        subject = subject_factory(subject.name)
        val = subject.get("my-prop")
        assert val == 1  # prop cached
        subject.set("my-prop", 8, cached=True)
        val = subject.get("my-prop", cached=False)  # update cache
        assert val == 1
        val = subject.get("my-prop", cached=True)
        assert val == 1
        subject.store()

    # deletes
    _test_events = []
    #   cache not loaded yet
    subject.delete("my-prop", cached=False)
    assert len(_test_events) == 1 and \
        _test_events[0][0] == types.SUBJECT_PROPERTY_DELETED and \
        _test_events[0][1].name == subject.name and \
        _test_events[0][2][PayloadConst.PROPERTY_NAME] == "my-prop"
    with pytest.raises(AttributeError):
        subject.get("my-prop")
    with pytest.raises(AttributeError):
        subject.delete("my-prop")
    # add prop bypassing cache
    subject.set("my-prop", 0, cached=False)
    subject.delete("my-prop", cached=True)
    subject.store()
    with pytest.raises(AttributeError):
        subject.get("my-prop")
    # add prop in cache remove directly
    subject.set("my-prop", 0, cached=True)
    subject.delete("my-prop", cached=False)
    subject.store()
    with pytest.raises(AttributeError):
        subject.get("my-prop")
    # all in cache
    subject.set("my-prop", 0, cached=True)
    subject.delete("my-prop", cached=True)
    subject.store()
    with pytest.raises(AttributeError):
        subject.get("my-prop")
    # no cache
    subject.set("my-prop", 0, cached=False)
    subject.delete("my-prop", cached=False)
    subject.store()
    with pytest.raises(AttributeError):
        subject.get("my-prop")


def test_get_ext_props(subject):

    # no cache
    subject.set("my-prop-1", 0, cached=False)
    subject.set_ext("my-prop-2", 2, cached=False)
    subject.set_ext("my-prop-3", 3, cached=False)

    props = subject.get_ext_props()
    assert len(props) == 2
    assert "my-prop-2" in props and props["my-prop-2"] == 2
    assert "my-prop-3" in props and props["my-prop-3"] == 3

    # with cache
    subject.set_ext("my-prop-4", 4, cached=True)
    subject.set("my-prop-5", 5, cached=True)
    props = subject.get_ext_props()
    assert len(props) == 3
    assert "my-prop-2" in props and props["my-prop-2"] == 2
    assert "my-prop-3" in props and props["my-prop-3"] == 3
    assert "my-prop-4" in props and props["my-prop-4"] == 4


def test_cache_policy(subject):
    from krules_core.providers import subject_factory, subject_storage_factory

    # default policy: use cache
    subject.flush()
    subject.set("p1", None)
    subject.set_ext("p2", None)

    subject_fresh = subject_factory(subject.name)
    with pytest.raises(AttributeError):
        subject_fresh.get("p1")
    with pytest.raises(AttributeError):
        subject_fresh.get_ext("p2")

    subject = subject_factory(subject.name, use_cache_default=False)
    subject.flush()
    subject.set("p1", None)
    subject.set_ext("p2", None)

    if subject_storage_factory(subject.name).is_persistent():
        subject_fresh = subject_factory(subject.name)
        subject_fresh.get("p1")
        subject_fresh.get_ext("p2")


# def test_incr_decr(subject):
#     from krules_core import messages
#     from krules_core.providers import subject_factory, subject_storage_factory
#
#     global _test_events
#     _test_events = []
#     # no cached values
#     subject.flush()
#     # no initial value
#     subject.incr("my-prop")
#     # already stored
#     if subject_storage_factory(subject.name).is_persistent():
#         assert subject_factory(subject.name).get("my-prop") == 1
#     # cache updated
#     assert subject.get("my-prop") == 1
#     subject.incr("my-prop", 2)
#     assert subject.get("my-prop") == 3
#     if subject_storage_factory(subject.name).is_persistent():
#         assert subject_factory(subject.name).get("my-prop") == 3
#     # forks with float
#     subject.incr("my-prop", .1)
#     assert subject.get("my-prop") == 3.1
#     # decr
#     subject.decr("my-prop", .1)
#     assert subject.get("my-prop") == 3
#
#     # check events
#     assert len(_test_events) == 4
#     expected_values = (
#         (messages.SUBJECT_PROPERTY_CHANGED, subject, {'old_value': None, 'property_name': 'my-prop', 'value': 1}),
#         (messages.SUBJECT_PROPERTY_CHANGED, subject, {'old_value': 1, 'property_name': 'my-prop', 'value': 3}),
#         (messages.SUBJECT_PROPERTY_CHANGED, subject, {'old_value': 3, 'property_name': 'my-prop', 'value': 3.1}),
#         (messages.SUBJECT_PROPERTY_CHANGED, subject, {'old_value': 3.1, 'property_name': 'my-prop', 'value': 3.0}),
#     )
#     for ev in range(len(_test_events)):
#         for i in range(len(_test_events[ev])):
#             assert expected_values[ev][i] == _test_events[ev][i]
#
#     # check mute
#     subject.incr("my-prop", muted=True)
#     subject.decr("my-prop", muted=True)
#     assert len(_test_events) == 4


def test_len(subject):

    subject.flush()
    subject.set("my-prop-1", 1)
    subject.set("my-prop-2", 2)
    subject.set_ext("my-prop-3", 3)

    assert len(subject) == 2

    subject.flush()
    assert len(subject) == 2


def test_iter_contains(subject):

    subject.flush()
    subject.set("my-prop-1", 1)
    subject.set("my-prop-2", 2)
    subject.set_ext("my-prop-3", 3)

    count = 0
    for k in subject:
        assert k in ("my-prop-1", "my-prop-2")
        count += 1
    assert count == 2

    for p in ("my-prop-1", "my-prop-2"):
        assert p in subject


def test_property_proxy(subject_no_cache):

    from krules_core.providers import subject_factory, subject_storage_factory
    global _test_events
    _test_events = []

    subject_no_cache.flush()

    with pytest.raises(AttributeError):
        _ = subject_no_cache.foo

    subject_no_cache.foo = 1
    assert subject_no_cache.foo == 1
    assert len(_test_events) == 1

    if subject_storage_factory(subject_no_cache.name).is_persistent():
        assert subject_factory(subject_no_cache.name).get("foo") == 1

    assert subject_no_cache.m_foo == 1
    assert subject_no_cache.foo == 1
    subject_no_cache.m_foo = 2
    assert len(_test_events) == 1

    subject_no_cache.ext_foo = 3
    assert subject_no_cache.ext_foo == 3
    assert subject_no_cache.foo == 2
    assert len(_test_events) == 1
    if subject_storage_factory(subject_no_cache.name).is_persistent():
        assert subject_factory(subject_no_cache.name).get_ext("foo") == 3

    subject_no_cache.foo = lambda foo: foo * foo
    assert len(_test_events) == 2

    assert subject_no_cache.foo == 4

    subject_no_cache.foo.incr()
    assert len(_test_events) == 3
    assert subject_no_cache.foo == 5
    subject_no_cache.m_foo.incr(2)
    assert len(_test_events) == 3
    assert subject_no_cache.foo == 7
    subject_no_cache.foo.decr()
    assert subject_no_cache.foo == 6
    with pytest.raises(TypeError):
        subject_no_cache.ext_foo.incr()
    with pytest.raises(TypeError):
        subject_no_cache.ext_foo.decr()

    del subject_no_cache.foo
    assert len(_test_events) == 5
    with pytest.raises(AttributeError):
        _ = subject_no_cache.foo
    subject_no_cache.foo = 1
    del subject_no_cache.m_foo
    assert len(_test_events) == 6
    with pytest.raises(AttributeError):
        _ = subject_no_cache.foo
    del subject_no_cache.ext_foo
    with pytest.raises(AttributeError):
        _ = subject_no_cache.ext_foo


def test_reading(subject):

    stringvalue = "abcde"
    intvalue = 8
    dictvalue = {"a": 1, "b": 2}
    tuplevalue = (1, 2, 3, 4)
    listvalue = [1, 2, 3, 4]

    subject.stringvalue = stringvalue
    subject.intvalue = intvalue
    subject.dictvalue = dictvalue
    subject.tuplevalue = tuplevalue
    subject.listvalue = listvalue
    subject.store()
    subject._load()

    assert subject.stringvalue == stringvalue
    assert subject.intvalue == intvalue
    assert subject.dictvalue == dictvalue
    assert subject.tuplevalue == list(tuplevalue)
    assert subject.listvalue == listvalue


