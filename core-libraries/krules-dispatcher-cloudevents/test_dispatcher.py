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

from krules_core.subject import PayloadConst


from pytest_localserver import http, plugin

from dependency_injector import providers

from krules_core.providers import (
    settings_factory,
    message_router_factory,
    message_dispatcher_factory,
    subject_factory)
from krules_core.route.router import MessageRouter
from .route.dispatcher import CloudEventsDispatcher

httpserver = plugin.httpserver


settings_factory.override(
    providers.Singleton(lambda: {})
)
message_router_factory.override(
    providers.Singleton(MessageRouter)
)

# TODO: use mock subject
settings_factory.override(
    providers.Singleton(lambda: {
        'SUBJECT_REDIS_CONNECT_KWARGS': {
            'host': 'localhost',
            'port': 6379,
            'db': 0,
        },
        'RKEY_PREFIX': 'pytest',
    })
)

from subject_redis.core import SubjectRedis
subject_factory.override(
    providers.Factory(SubjectRedis)
)

def test_dispatched_event(httpserver):
    from krules_core import messages

    message_dispatcher_factory.override(
        providers.Singleton(lambda: CloudEventsDispatcher(httpserver.url, "pytest", test=True))
    )
    router = message_router_factory()
    subject = subject_factory("test-subject")
    subject.set_ext("ext1", "val1")
    subject.set_ext("ext2", 2)
    _id, code, sent_headers = router.route("test-message", subject, {"key1": "hello"})
    assert(200 <= code < 300)
    assert (sent_headers.get("Ce-Id") == _id)
    assert(sent_headers.get("Ce-Source") == "pytest")
    assert(sent_headers.get("Ce-Subject") == "test-subject")
    assert(sent_headers.get("Ce-Type") == "test-message")
    assert(sent_headers.get("Ce-Originid") == _id)
    assert(sent_headers.get("Ce-Ext1") == "val1")
    assert(sent_headers.get("Ce-Ext2") == "2")

    # with event info
    subject = subject_factory("test-subject", event_info={"Originid": 1234})
    _, _, sent_headers = router.route("test-message", subject, {"key1": "hello"})
    assert(sent_headers.get("Ce-Id") != sent_headers.get("Ce-Originid"))
    assert(sent_headers.get("Ce-Originid") == '1234')

    # property name
    _, _, sent_headers = router.route(messages.SUBJECT_PROPERTY_CHANGED, subject, {PayloadConst.PROPERTY_NAME: "foo"})
    assert (sent_headers.get("Ce-Propertyname") == 'foo')



