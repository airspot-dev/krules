from krules_core.providers import event_dispatcher_factory, subject_storage_factory
from krules_cloudevents_pubsub.route.dispatcher import CloudEventsDispatcher
from dependency_injector import providers
from krules_env import get_source, RULE_PROC_EVENT
import os
import google.auth
from redis_subjects_storage.storage_impl import SubjectsRedisStorage



TOPIC_NAME = os.environ.get("PUBSUB_SINK")
if TOPIC_NAME is None:
    raise EnvironmentError("PUBSUB_SINK must be defined")

_, PROJECT = google.auth.default()


def _get_topic_id(subject, event_type):

    if event_type == RULE_PROC_EVENT:
        topic_name = os.environ.get("PUBSUB_PROCEVENTS_SINK")
        if topic_name is None:
            raise EnvironmentError("PUBSUB_PROCEVENTS_SINK must be defined")
        if os.environ.get("PUBSUB_PROCEVENTS_SINK_PROJECT"):
            return f"projects/{os.environ.get('PUBSUB_PROCEVENTS_SINK_PROJECT')}/topics/{topic_name}"
    else:
        topic_name = TOPIC_NAME

    return topic_name


def init():
    event_dispatcher_factory.override(
        providers.Singleton(lambda: CloudEventsDispatcher
            (
                project_id=PROJECT,
                topic_id=_get_topic_id,
                source=get_source(),
            )
        )
    )

    subjects_redis_url = os.environ.get("SUBJECTS_REDIS_URL")
    if subjects_redis_url is not None:
        subjects_redis_prefix = os.environ.get("SUBJECTS_REDIS_PREFIX")
        if subjects_redis_prefix is None:
            if "PROJECT_NAME" in os.environ and "TARGET" in os.environ:
                subjects_redis_prefix=f"{os.environ['PROJECT_NAME']}-{os.environ['TARGET']}->"
            else:
                raise Exception("SUBJECTS_REDIS_PREFIX not configured")
        subject_storage_factory.override(
            providers.Factory(
                lambda name, **kwargs:
                SubjectsRedisStorage(
                    name,
                    subjects_redis_url,
                    key_prefix=subjects_redis_prefix
                )
            )
        )
