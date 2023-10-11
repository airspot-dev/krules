from krules_core.providers import event_dispatcher_factory, subject_storage_factory
from krules_cloudevents_pubsub.route.dispatcher import CloudEventsDispatcher
from dependency_injector import providers
from krules_env import get_source, RULE_PROC_EVENT
import os
import google.auth
from redis_subjects_storage.storage_impl import SubjectsRedisStorage
from google.cloud import secretmanager
import re
import logging

logger = logging.getLogger()


_, PROJECT = google.auth.default()
APP_PROJECT = os.environ.get("APPLICATION_PROJECT_ID", PROJECT)
PROJECT_NAME = os.environ['PROJECT_NAME']
TARGET = os.environ['TARGET']


TOPIC_NAME = os.environ.get(
    "PUBSUB_SINK",
    f"projects/{APP_PROJECT}/topics/{PROJECT_NAME}-default-sink-{TARGET}"
)


def _get_topic_id(subject, event_type):

    if event_type == RULE_PROC_EVENT:
        topic_name = os.environ.get("PUBSUB_PROCEVENTS_SINK", f"{PROJECT_NAME}-procevents-{TARGET}")
        return f"projects/{os.environ.get('PUBSUB_PROCEVENTS_SINK_PROJECT_ID', APP_PROJECT)}/topics/{topic_name}"
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
    if subjects_redis_url is None:
        secretmanager_project_id = os.environ.get("SECRETMANAGER_PROJECT_ID", APP_PROJECT)
        secret_name = f"{os.environ['PROJECT_NAME']}-subjects_redis_url-{os.environ['TARGET']}"
        client = secretmanager.SecretManagerServiceClient()
        secret_path = client.secret_version_path(
            secretmanager_project_id, secret_name, os.environ.get("SUBJECTS_REDIS_URL_SECRET_VERSION", "latest")
        )
        response = client.access_secret_version(name=secret_path)
        subjects_redis_url = response.payload.data.decode('utf-8')
    subjects_redis_prefix = os.environ.get("SUBJECTS_REDIS_PREFIX")
    if subjects_redis_prefix is None:
        if "PROJECT_NAME" in os.environ and "TARGET" in os.environ:
            subjects_redis_prefix = f"{os.environ['PROJECT_NAME']}-{os.environ['TARGET']}->"
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
