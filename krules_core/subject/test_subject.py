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


from krules_core.subject import PayloadConst

_test_messages = []
class Router(object):

    def route(self, message, name, payload):
        _test_messages.append((message, name, payload))


def setup_module(_):
    from dependency_injector import providers as providers
    from krules_core.providers import message_router_factory

    message_router_factory.override(
        providers.Singleton(Router)
    )



counter = 0


@pytest.fixture
def messages():
    from krules_core import ConfigKeyConst
    from krules_core.providers import settings_factory
    settings_factory.override(
        providers.Singleton(
            lambda: {
                ConfigKeyConst.MESSAGE_TOPICS_PREFIX: "tests-"
            }
        )
    )
    from krules_core import messages
    return messages


@pytest.fixture
def subject(messages):

    _ = messages

    from krules_core.providers import subject_factory

    global counter
    counter += 1
    return subject_factory('test-subject-{0}'.format(counter)).flush()


def test_non_existent_attribute(subject):

    with pytest.raises(AttributeError):
        _ = subject.foo
    with pytest.raises(AttributeError):
        getattr(subject, "foo")


def test_flush(subject):

    subject.foo = 1
    assert subject.foo == 1
    subject.flush()
    with pytest.raises(AttributeError):
        getattr(subject, "foo")


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

    assert subject.stringvalue == stringvalue
    assert subject.intvalue == intvalue
    assert subject.dictvalue == dictvalue
    assert list(subject.tuplevalue) == list(tuplevalue)  # tuples may be not supported
    assert subject.listvalue == listvalue


def test_removing(subject):

    from krules_core import messages

    s_name = subject.name
    subject.foo = 1
    delattr(subject, "foo")

    v_message, v_test_subject_name, v_payload = _test_messages.pop()
    assert v_message == messages.SUBJECT_PROPERTY_DELETED
    assert v_test_subject_name == s_name
    assert v_payload[PayloadConst.PROPERTY_NAME] == "foo"
    assert v_payload[PayloadConst.VALUE] == 1
    with pytest.raises(AttributeError):
        _ = subject.foo
    with pytest.raises(AttributeError):
        getattr(subject, "foo")


def test_incr_decr(subject):

    from krules_core import messages

    subject.foo = 1
    v_message, v_subject_id, v_payload = _test_messages.pop()
    assert v_message == messages.SUBJECT_PROPERTY_CHANGED
    assert v_payload[PayloadConst.PROPERTY_NAME] == 'foo'
    assert v_payload[PayloadConst.OLD_VALUE] is None
    assert v_payload[PayloadConst.VALUE] == 1

    ret = subject.foo.incr(5)
    assert ret == 6
    assert subject.foo == 6
    v_messages, v_subject_id, v_payload = _test_messages.pop()
    assert v_message == messages.SUBJECT_PROPERTY_CHANGED
    assert v_payload[PayloadConst.PROPERTY_NAME] == 'foo'
    assert v_payload[PayloadConst.OLD_VALUE] == 1
    assert v_payload[PayloadConst.VALUE] == 6

    ret = subject.foo.decr(1)
    assert ret == 5
    assert subject.foo == 5
    v_message, v_subject_id, v_payload = _test_messages.pop()
    assert v_message, messages.SUBJECT_PROPERTY_CHANGED
    assert v_payload[PayloadConst.PROPERTY_NAME] == 'foo'
    assert v_payload[PayloadConst.OLD_VALUE] == 6
    assert v_payload[PayloadConst.VALUE] == 5

    subject.moo = "string"
    with pytest.raises(AttributeError):  # 'str' object has no attribute 'incr'
        subject.moo.incr(1)
    with pytest.raises(AttributeError):  # 'str' object has no attribute 'decr'
        subject.moo.decr(1)
    _test_messages.pop()


def test_iterable(subject):

    subject.attr1 = "1"
    subject.attr2 = 2

    assert 'attr1' in subject
    assert 'attr2' in subject
    assert 'attr3' not in subject


