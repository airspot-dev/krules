from dependency_injector import providers as providers
from krules_core.providers import (
    subject_storage_factory,
)


def init():

    from k8s_subjects_storage import storage_impl as k8s_storage_impl
    subject_storage_factory.override(
       providers.Factory(lambda name, event_info, event_data:
                         k8s_storage_impl.SubjectsK8sStorage(
                                                resource_path=name,
                                                resource_body=event_data
                         ))
    )

