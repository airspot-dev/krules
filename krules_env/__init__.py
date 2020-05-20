
import inspect
import json
import os
import socket
import jsonpath_rw_ext as jp

import rx
import yaml
from dependency_injector import providers

from krules_core import TopicsDefault, RuleConst
from krules_core.exceptions_dumpers import ExceptionDumperBase, RequestsHTTPErrorDumper

from krules_core.providers import (
    settings_factory,
    subject_factory,
    results_rx_factory,
    message_router_factory,
    message_dispatcher_factory,
    exceptions_dumpers_factory,
)
from krules_core.route.router import DispatchPolicyConst, MessageRouter

config_base_path = os.environ.get("KRULES_CONFIG_BASE_PATH", "/krules/config")

from krules_env.settings_loader import load_from_path
krules_settings = load_from_path(config_base_path)


class _JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if inspect.isfunction(obj):
            return obj.__name__
        elif isinstance(obj, object):
            return str(type(obj))
        return json.JSONEncoder.default(self, obj)


def publish_results_all(result):

    from krules_core.messages import format_message_name

    topic_name = os.environ.get("RESULTS_TOPIC", format_message_name(TopicsDefault.RESULTS))
    if topic_name == "-":
        return

    data = json.loads(json.dumps(result, cls=_JSONEncoder).encode("utf-8"))

    event_info = data[RuleConst.PAYLOAD].get("_event_info", {})
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

    exceptions_dumpers = exceptions_dumpers_factory()
    exceptions_dumpers.set(ExceptionDumperBase)
    exceptions_dumpers.set(RequestsHTTPErrorDumper)

    # TODO: do it better
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


