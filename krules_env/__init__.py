
import inspect
import json
import os
import socket
import jsonpath_rw_ext as jp

import rx
import yaml
from dependency_injector import providers

from krules_core import RuleConst
from krules_core.exceptions_dumpers import ExceptionDumperBase, RequestsHTTPErrorDumper

from krules_core.providers import (
    configs_factory,
    subject_factory,
    proc_events_rx_factory,
    event_router_factory,
    event_dispatcher_factory,
    exceptions_dumpers_factory,
)
from krules_core.route.router import DispatchPolicyConst, EventRouter
from krules_core.types import format_event_type

config_base_path = os.environ.get("KRULES_CONFIG_BASE_PATH", "/krules/config")

from krules_env.settings_loader import load_from_path
krules_settings = load_from_path(config_base_path)

RULE_PROC_EVENT = format_event_type("rule-proc-event")


# class _JSONEncoder(json.JSONEncoder):
#     def default(self, obj):
#         if inspect.isfunction(obj):
#             return obj.__name__
#         elif isinstance(obj, object):
#             return str(type(obj))
#         return json.JSONEncoder.default(self, obj)


def publish_proc_events_all(result):

    data = result
    # data = json.loads(json.dumps(result, cls=_JSONEncoder).encode("utf-8"))
    event_info = data.get("event_info", {})
    result_subject = subject_factory(data[RuleConst.RULENAME], event_info=event_info)

    event_router_factory().route(
        RULE_PROC_EVENT, result_subject, data, dispatch_policy=DispatchPolicyConst.DIRECT
    )


# TODO: wrap filtered
def publish_proc_events_errors(result):

    if not result.get("got_errors", False):
        return

    data = result
    # data = json.loads(json.dumps(result, cls=_JSONEncoder).encode("utf-8"))

    event_info = data["event_info"]
    result_subject = subject_factory(data[RuleConst.RULENAME], event_info=event_info)

    event_router_factory().route(
        RULE_PROC_EVENT, result_subject, data, dispatch_policy=DispatchPolicyConst.DIRECT
    )


def publish_proc_events_filtered(result, jp_expr, expt_value):

    if callable(expt_value):
        _pass = expt_value(jp.match1(jp_expr, result))
    else:
        _pass = (jp.match1(jp_expr, result) == expt_value)
    if not _pass:
        return

    data = result
    # data = json.loads(json.dumps(result, cls=_JSONEncoder).encode("utf-8"))

    event_info = data["event_info"]
    result_subject = subject_factory(data[RuleConst.RULENAME], event_info=event_info)

    event_router_factory().route(
        RULE_PROC_EVENT, result_subject, data, dispatch_policy=DispatchPolicyConst.DIRECT
    )


def _get_dispatch_url(subject, type):
    ksink = os.environ.get("K_SINK")
    if type == RULE_PROC_EVENT and "K_PROCEVENTS_SINK" in os.environ:
        return os.environ.get("K_PROCEVENTS_SINK")
    if ksink is not None:
        return ksink
    return krules_settings["CLOUDEVENTS"]["send_to"]


def init():
    configs_factory.override(
        providers.Singleton(lambda: krules_settings)
    )

    proc_events_rx_factory.override(
        providers.Singleton(rx.subjects.ReplaySubject)
    )

    event_router_factory.override(
        providers.Singleton(lambda: EventRouter())
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
    event_dispatcher_factory.override(
        providers.Singleton(lambda: CloudEventsDispatcher
            (
                _get_dispatch_url,
                source
            )
        )
    )
