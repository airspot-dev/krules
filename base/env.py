from dependency_injector import providers as providers
from krules_core.providers import (
    subject_storage_factory,
)
from krules_core.subject.empty_storage import EmptySubjectStorage


def init():

    from k8s_subjects_storage import storage_impl as k8s_storage_impl
    subject_storage_factory.override(
       providers.Factory(lambda name, event_info, event_data:
                         name.startswith("k8s:") and k8s_storage_impl.SubjectsK8sStorage(
                                                        resource_path=name[4:],
                                                        resource_body=event_data.get("object")
                         ) or EmptySubjectStorage())
    )

    # # WORKAROUND: see KRUL-182
    # from krules_cloudevents.route.dispatcher import CloudEventsDispatcher
    # from krules_core.providers import event_dispatcher_factory
    # import os, socket
    # event_dispatcher_factory.override(
    #     providers.Singleton(lambda: CloudEventsDispatcher(os.environ["K_SINK"],
    #                                                       os.environ.get("RULESET", socket.gethostname())))
    # )