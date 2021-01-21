import inspect

from dependency_injector import providers as providers
from krules_core.arg_processors import BaseArgProcessor, processors
from krules_core.providers import (
    subject_storage_factory,
    configs_factory
)
import os

def init():
    # This is an inmemory database and it is not persistent
    # you probably want to comment out this configuration and enable a more appropriate one

    from krules_core.tests.subject.sqlite_storage import SQLLiteSubjectStorage
    from k8s_subjects_storage import storage_impl as k8s_storage_impl

    from redis_subjects_storage import storage_impl as redis_storage_impl
    subjects_redis_storage_settings = configs_factory() \
        .get("subjects-backends") \
        .get("redis")

    subject_storage_factory.override(
        providers.Factory(lambda name, event_info, event_data:
                            name.startswith("k8s:") and k8s_storage_impl.SubjectsK8sStorage(
                              resource_path=name[4:],
                              resource_body=event_data
                            )
                            or redis_storage_impl.SubjectsRedisStorage(name, subjects_redis_storage_settings.get("url"))
                          )
    )

    from krules_cloudevents.route.dispatcher import CloudEventsDispatcher
    from krules_core.providers import event_dispatcher_factory
    import os, socket
    event_dispatcher_factory.override(
        providers.Singleton(lambda: CloudEventsDispatcher(os.environ["K_SINK"],
                                                          os.environ.get("K_SERVICE", socket.gethostname())))
    )

    class CallableWithCtxArgProcessor(BaseArgProcessor):

        @staticmethod
        def interested_in(arg):
            try:
                sig = inspect.signature(arg)
                return len(sig.parameters) == 1 and "ctx" in sig.parameters or "_" in sig.parameters
            except TypeError:
                return False

        def process(self, instance):
            return self._arg(instance)

    processors.append(CallableWithCtxArgProcessor)
