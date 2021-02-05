import json
import os
import sys
import logging
from datetime import datetime
import json_logging
import importlib

from dependency_injector import providers
from flask import Flask
from flask import Response
from flask import request
from flask import g

from krules_core.route.router import DispatchPolicyConst
from krules_core.providers import event_router_factory
from krules_core.utils import load_rules_from_rulesdata


import krules_env
import env as app_env
import io

from cloudevents.sdk.event import v1
from cloudevents.sdk import marshaller

from krules_core.subject.storaged_subject import Subject

from krules_core.providers import (
            subject_factory,
        )

from flask_g_wrap import g_wrap

app = Flask("ruleset")

json_logging.ENABLE_JSON_LOGGING = True
json_logging.init_flask()
json_logging.init_request_instrument(app)

# app.logger.setLevel(int(os.environ.get("LOGGING_LEVEL", logging.INFO)))
# app.logger.propagate = False

# TODO: KRUL-47
logger = logging.getLogger(app.name)
logger.setLevel(int(os.environ.get("LOGGING_LEVEL", logging.INFO)))
logger.addHandler(logging.StreamHandler(sys.stdout))
logger.propagate = False

logger_core = logging.getLogger("__core__")
logger_core.setLevel(int(os.environ.get("CORE_LOGGING_LEVEL", logging.ERROR)))
logger_core.addHandler(logging.StreamHandler(sys.stdout))
logger_core.propagate = False

logger_router = logging.getLogger("__router__")
logger_router.setLevel(int(os.environ.get("ROUTER_LOGGING_LEVEL", logging.ERROR)))
logger_router.addHandler(logging.StreamHandler(sys.stdout))
logger_router.propagate = False

req_logger = logging.getLogger("flask-request-logger")
req_logger.setLevel(logging.ERROR)
req_logger.propagate = False

krules_env.init()
app_env.init()
subject_factory.override(providers.Factory(lambda *args, **kw: g_wrap(subject_factory.cls, *args, **kw)))

try:
    m_rules = importlib.import_module("ruleset")
except ModuleNotFoundError:
    m_rules = importlib.import_module("rules")


load_rules_from_rulesdata(m_rules.rulesdata)


@app.route('/', methods=['POST'])
def main():
    start_time = datetime.now()
    try:
        dispatch_policy = os.environ.get("DISPATCH_POLICY", DispatchPolicyConst.NEVER)

        m = marshaller.NewDefaultHTTPMarshaller()
        event = m.FromRequest(v1.Event(), request.headers, io.BytesIO(request.data), lambda x: json.load(x))
        event_info = event.Properties()
        event_info.update(event_info.pop("extensions"))
        event_data = event_info.pop("data")

        app.logger.debug("RCVR: {}".format(event_data))
        event_type = event_info.get("type")
        subject = event_info.get("subject", "sys-0")

        g.subjects = []
        # TODO: stiil deeded ? (block from same source)
        if event_info["source"] == os.environ.get("K_SERVICE", os.environ.get("SOURCE")):
            return Response(status=201)

        event_info["originid"] = event_info.get("originid", event_info.get("id"))

        logger.debug("subject: {}".format(subject))
        logger.debug("event_data: {}".format(event_data))

        from dependency_injector import providers

        subject = subject_factory(name=subject, event_info=event_info, event_data=event_data)

        event_data["_event_info"] = event_info  # TODO: KRUL-155

        try:
            event_router_factory().route(
                event_type, subject, event_data,
                dispatch_policy=dispatch_policy
            )
        finally:
            for sub in g.subjects:
                sub.store()

        exec_time = (datetime.now() - start_time).total_seconds()
        logger.info("Event",
                    extra={'props': {
                                'event_info': event_info,
                                'type': event_type,
                                'subject': subject.name,
                                'exec_time': exec_time,
                                #'headers': list(headers.keys())
                    }})
        return Response(status=200)

    except Exception as ex:
        app.logger.error(ex, exc_info=True)
        return Response(status=201)
