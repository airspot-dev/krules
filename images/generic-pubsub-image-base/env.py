from krules_core.providers import event_dispatcher_factory
from krules_cloudevents_pubsub.route.dispatcher import CloudEventsDispatcher
from dependency_injector import providers
from krules_env import get_source, RULE_PROC_EVENT
import os
import google.auth


TOPIC_PREFIX = os.environ.get("PUBSUB_SINK")
if TOPIC_PREFIX is None:
    raise EnvironmentError("PUBSUB_SINK must be defined")

TARGET = os.environ.get("ENV_TARGET")
if TARGET is None:
    raise EnvironmentError("ENV_TARGET must be defined in environ")

_, PROJECT = google.auth.default()


def _get_topic_id(subject, event_type):

    if event_type == RULE_PROC_EVENT:
        topic_prefix = os.environ.get("PUBSUB_PROCEVENTS_SINK")
        if topic_prefix is None:
            raise EnvironmentError("PUBSUB_PROCEVENTS_SINK must be defined")
        if os.environ.get("PUBSUB_PROCEVENTS_SINK_PROJECT"):
            return f"projects/{os.environ.get('PUBSUB_PROCEVENTS_SINK_PROJECT')}/topics/{topic_prefix}"
    else:
        topic_prefix = TOPIC_PREFIX

    return f"{topic_prefix}-{TARGET}"


def init():
    event_dispatcher_factory.override(
        providers.Singleton(lambda: CloudEventsDispatcher
            (
                project_id=PROJECT,
                topic_id=_get_topic_id,
                source=get_source()
            )

        )
    )
