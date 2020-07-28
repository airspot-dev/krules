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
from krules_core.subject import PayloadConst


from pytest_localserver import plugin

from dependency_injector import providers

from krules_core.providers import (
    configs_factory,
    event_router_factory,
    event_dispatcher_factory,
    subject_storage_factory,
    subject_factory)
from krules_core.route.router import EventRouter
from .route.dispatcher import CloudEventsDispatcher
from krules_core.tests.subject.sqlite_storage import SQLLiteSubjectStorage

httpserver = plugin.httpserver


configs_factory.override(
    providers.Singleton(lambda: {})
)
event_router_factory.override(
    providers.Singleton(EventRouter)
)

subject_storage_factory.override(
    providers.Factory(lambda x: SQLLiteSubjectStorage(x, ":memory:"))
)


def test_dispatched_event(httpserver):
    from krules_core import types

    event_dispatcher_factory.override(
        providers.Singleton(lambda: CloudEventsDispatcher(httpserver.url, "pytest", test=True))
    )
    router = event_router_factory()
    subject = subject_factory("test-subject")
    subject.set_ext("ext1", "val1")
    subject.set_ext("ext2", "2")
    _id, code, sent_headers = router.route("test-type", subject, {"key1": "hello"})
    print(sent_headers)

    assert(200 <= code < 300)
    assert (sent_headers.get("ce-id") == _id)
    assert(sent_headers.get("ce-source") == "pytest")
    assert(sent_headers.get("ce-subject") == "test-subject")
    assert(sent_headers.get("ce-type") == "test-type")
    assert(sent_headers.get("ce-Originid") == _id)
    assert(sent_headers.get("ce-ext1") == "val1")
    assert(sent_headers.get("ce-ext2") == "2")

    # with event info
    subject = subject_factory("test-subject", event_info={"Originid": 1234})
    _, _, sent_headers = router.route("test-type", subject, {"key1": "hello"})
    assert(sent_headers.get("id") != sent_headers.get("ce-Originid"))
    assert(sent_headers.get("ce-Originid") == '1234')

    # property name
    _, _, sent_headers = router.route(types.SUBJECT_PROPERTY_CHANGED, subject, {PayloadConst.PROPERTY_NAME: "foo"})
    assert (sent_headers.get("ce-propertyname") == 'foo')



