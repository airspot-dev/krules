
import inspect
import json
import os
import socket
import jsonpath_rw_ext as jp

import redis
import rx
import yaml
from dependency_injector import providers

from krules_core import TopicsDefault, RuleConst
from subject_redis import ConfigKeyConst as RedisConfigKeyConst

from krules_core.providers import message_router_factory
from krules_core.providers import (
    settings_factory,
    subject_factory,
    results_rx_factory,
    message_router_factory,
    message_dispatcher_factory,
)
from krules_core.route.router import DispatchPolicyConst, MessageRouter
from subject_redis.providers import redis_client_factory

config_path = os.environ.get("KRULES_CONFIG_PATH", "/krules/config/config_krules.yaml")
krules_settings = yaml.load(open(config_path, "r"), Loader=yaml.FullLoader)


class RulesConst(object):
    pass

# TODO: DO IT BETTER (maybe in dispatcher)

class _JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        from krules_core.base_functions import with_subject, with_payload, with_self
        if isinstance(obj, with_self) or isinstance(obj, with_payload) or isinstance(obj, with_subject):
            return obj.result()
        elif inspect.isfunction(obj):
            return obj.__name__
        elif isinstance(obj, object):
            return str(type(obj))
        return json.JSONEncoder.default(self, obj)


# TODO wrap filtered
def publish_results_all(result):

    from krules_core.messages import format_message_name

    topic_name = os.environ.get("RESULTS_TOPIC", format_message_name(TopicsDefault.RESULTS))
    if topic_name == "-":
        return

    data = json.loads(json.dumps(result, cls=_JSONEncoder).encode("utf-8"))

    event_info = data[RuleConst.PAYLOAD]["_event_info"]
    result_subject = subject_factory(data[RuleConst.RULE_NAME], event_info=event_info)

    message_router_factory().route(
        topic_name, result_subject, data, dispatch_policy=DispatchPolicyConst.DIRECT
    )

# TODO: wrap filtered
def publish_results_errors(result):

    from krules_core.messages import format_message_name

    topic_name = os.environ.get("RESULTS_TOPIC", format_message_name(TopicsDefault.RESULTS))
    if topic_name == "-":
        return

    if not result.get("got_errors", False):
        return

    data = json.loads(json.dumps(result, cls=_JSONEncoder).encode("utf-8"))

    event_info = data[RuleConst.PAYLOAD]["_event_info"]
    result_subject = subject_factory(data[RuleConst.RULE_NAME], event_info=event_info)

    message_router_factory().route(
        topic_name, result_subject, data, dispatch_policy=DispatchPolicyConst.DIRECT
    )



def publish_results_filtered(result, jp_expr, expt_value):

    from krules_core.messages import format_message_name

    topic_name = os.environ.get("RESULTS_TOPIC", format_message_name(TopicsDefault.RESULTS))

    if callable(expt_value):
        _pass = expt_value(jp.match1(jp_expr, result))
    else:
        _pass = (jp.match1(jp_expr, result) == expt_value)
    if not _pass:
        return

    data = json.loads(json.dumps(result, cls=_JSONEncoder).encode("utf-8"))

    event_info = data[RuleConst.PAYLOAD]["_event_info"]
    result_subject = subject_factory(data[RuleConst.RULE_NAME], event_info=event_info)

    message_router_factory().route(
        topic_name, result_subject, data, dispatch_policy=DispatchPolicyConst.DIRECT
    )


def init():
    settings_factory.override(
        providers.Singleton(lambda: krules_settings)
    )

    results_rx_factory.override(
        providers.Singleton(rx.subjects.ReplaySubject)
    )

    message_router_factory.override(
        providers.Singleton(lambda: MessageRouter(multiprocessing=False))
    )

    source = None
    if "K_SERVICE" in os.environ:
        source = os.environ["K_SERVICE"]
    elif "SERVICE" in os.environ:
        source = os.environ["SERVICE"]
    else:
        source = socket.gethostname()

    from krules_cloudevents.route.dispatcher import CloudEventsDispatcher
    message_dispatcher_factory.override(
        providers.Singleton(lambda: CloudEventsDispatcher(krules_settings["CLOUDEVENTS"]["send_to"], source))
    )


