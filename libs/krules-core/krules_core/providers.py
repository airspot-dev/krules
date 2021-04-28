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


from rx import subject, from_future

from dependency_injector import providers as providers
from krules_core.subject.empty_storage import EmptySubjectStorage

from .route.dispatcher import BaseDispatcher
from .route.router import EventRouter
from .subject.storaged_subject import Subject
from .exceptions_dumpers import ExceptionsDumpers


configs_factory = providers.Singleton(lambda: {})

# for testing/development only
subject_storage_factory = providers.Factory(lambda *args, **kwargs: EmptySubjectStorage())

subject_factory = providers.Factory(Subject)
proc_events_rx_factory = providers.Singleton(subject.ReplaySubject)
# proc_events_rx_factory = subject.ReplaySubject()
event_router_factory = providers.Singleton(EventRouter)
event_dispatcher_factory = providers.Singleton(BaseDispatcher)
exceptions_dumpers_factory = providers.Singleton(ExceptionsDumpers)
