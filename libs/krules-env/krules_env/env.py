import importlib
import logging
import os
import sys

import jsonpath_rw_ext as jp
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
from krules_core.utils import load_rules_from_rulesdata, get_source

config_base_path = os.environ.get("KRULES_CONFIG_BASE_PATH", "/krules/config")

from .settings_loader import load_from_path
krules_settings = load_from_path(config_base_path)

RULE_PROC_EVENT = "rule-proc-event"

logger = logging.getLogger("__env__")
logger.setLevel(logging.WARNING)
logger.addHandler(logging.StreamHandler(sys.stdout))
logger.propagate = False


# class _JSONEncoder(json.JSONEncoder):
#     def default(self, obj):
#         if inspect.isfunction(obj):
#             return obj.__name__
#         elif isinstance(obj, object):
#             return str(type(obj))
#         return json.JSONEncoder.default(self, obj)


def publish_proc_events_all(result, debug=False):

    publish_proc_events_filtered(result, None, None, debug)


def publish_proc_events_errors(result, debug=False):

    publish_proc_events_filtered(result, "got_errors=true", lambda x: x is not None, debug)


def publish_proc_events_filtered(result, jp_expr, expt_value, debug=False):
    if jp_expr is not None:
        if not isinstance(jp_expr, list):
            jp_expr = [jp_expr]
        for expr in jp_expr:
            if callable(expt_value):
                _pass = expt_value(jp.match1(f"$[?({expr})]", [result]))
            else:
                _pass = (jp.match1(f"$[?({expr})]", [result]) == expt_value)
            if not _pass:
                return

    data = result

    event_info = data["event_info"]
    result_subject = subject_factory(data[RuleConst.RULENAME], event_info=event_info)

    if debug and result["type"] != RULE_PROC_EVENT:
        dispatch_policy = DispatchPolicyConst.NEVER
    else:
        dispatch_policy = DispatchPolicyConst.DIRECT
    event_router_factory().route(
        RULE_PROC_EVENT, result_subject, data, dispatch_policy=dispatch_policy
    )


def _get_dispatch_url(subject, event_type):
    ksink = os.environ.get("K_SINK")
    if event_type == RULE_PROC_EVENT: 
        ksink = os.environ.get("K_PROCEVENTS_SINK", ksink)
    if ksink is not None:
        return ksink
    return krules_settings["CLOUDEVENTS"]["send_to"]


def init():
    configs_factory.override(
        providers.Singleton(lambda: krules_settings)
    )

    event_router_factory.override(
        providers.Singleton(lambda: EventRouter())
    )

    exceptions_dumpers = exceptions_dumpers_factory()
    exceptions_dumpers.set(ExceptionDumperBase)
    exceptions_dumpers.set(RequestsHTTPErrorDumper)

    from krules_cloudevents.route.dispatcher import CloudEventsDispatcher
    event_dispatcher_factory.override(
        providers.Singleton(lambda: CloudEventsDispatcher
            (
                _get_dispatch_url,
                get_source()
            )
        )
    )

    try:
        import env
        if "init" in dir(env) and callable(env.init):
            env.init()
    except ModuleNotFoundError as ex:
        if ex.name == "env":
            logger.warning("No application env.py found!")
        else:
            raise ex
    try:
        import __init__
    except ModuleNotFoundError as ex:
        if not ex.name == "__init__":
            raise ex

    try:
        m_rules = importlib.import_module("ruleset")
        load_rules_from_rulesdata(m_rules.rulesdata)
    except ModuleNotFoundError as ex:
        if ex.name == "ruleset":
            logger.warning("No rules defined!")
        else:
            raise ex

    proc_events_filters = os.environ.get("PUBLISH_PROCEVENTS_MATCHING")
    if proc_events_filters:
        proc_events_rx_factory().subscribe(
            on_next=lambda x: publish_proc_events_filtered(x, proc_events_filters.split(";"),
                                                           lambda match: match is not None)
        )
    else:
        proc_events_rx_factory().subscribe(
            on_next=lambda x: publish_proc_events_all(x)
        )
