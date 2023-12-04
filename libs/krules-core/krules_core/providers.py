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


from dependency_injector import providers as di_providers
from krules_core.subject.empty_storage import EmptySubjectStorage
from rx import subject

from .exceptions_dumpers import ExceptionsDumpers
from .route.dispatcher import BaseDispatcher
from .route.router import EventRouter
from .subject.storaged_subject import Subject

configs_factory = di_providers.Singleton(lambda: {})

# for testing/development only
subject_storage_factory = di_providers.Factory(lambda *args, **kwargs: EmptySubjectStorage())

subject_factory = di_providers.Factory(Subject)
proc_events_rx_factory = di_providers.Singleton(subject.ReplaySubject)
# proc_events_rx_factory = subject.ReplaySubject()
event_router_factory = di_providers.Singleton(EventRouter)
event_dispatcher_factory = di_providers.Singleton(BaseDispatcher)
exceptions_dumpers_factory = di_providers.Singleton(ExceptionsDumpers)
