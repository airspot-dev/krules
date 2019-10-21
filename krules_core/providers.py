import rx

from dependency_injector import providers as providers

from .route.dispatcher import BaseDispatcher
from .route.router import MessageRouter
from .subject.tests.mocksubject import MockSubject

import logging
logger = logging.getLogger(__name__)

settings_factory = providers.Singleton(object)

subject_factory = providers.Singleton(MockSubject)
results_rx_factory = providers.Singleton(rx.subjects.ReplaySubject)
message_router_factory = providers.Singleton(MessageRouter)
message_dispatcher_factory = providers.Singleton(BaseDispatcher)


