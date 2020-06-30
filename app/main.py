import json
import os
import sys
import logging
from datetime import datetime
import json_logging
import importlib

from flask import Flask
from flask import Response
from flask import request

from krules_core.route.router import DispatchPolicyConst
from krules_core.providers import message_router_factory
from krules_core.utils import load_rules_from_rulesdata


import krules_env
import env as app_env
import io

from cloudevents.sdk.event import v1
from cloudevents.sdk import marshaller

app = Flask("rulesset")

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

        payload = event.Data()

        app.logger.debug("RCVR: {}".format(payload))
        message = event_info.get("type")
        subject = event_info.get("subject", "sys-0")


        # TODO: important!!
        # need to find a way to avoid a return of messages from the same service
        # (for example when resending it again after intercepted in the first time)
        # this workaround only works when in a knative service or at least when SOURCE environment
        # variable is set

        if event_info["source"] == os.environ.get("K_SERVICE", os.environ.get("SOURCE")):
            return Response(status=201)

        event_info["Originid"] = event_info.get("originid", event_info.get("id"))

        logger.debug("subject: {}".format(subject))
        logger.debug("payload: {}".format(payload))

        from dependency_injector import providers
        from krules_core.providers import (
            subject_factory,
        )

        subject = subject_factory(subject, event_info=event_info)

        payload["_event_info"] = event_info

        try:
            message_router_factory().route(
                message, subject, payload,
                dispatch_policy=dispatch_policy
            )
        finally:
            subject.store()

        exec_time = (datetime.now() - start_time).total_seconds()
        logger.info("Event",
                    extra={'props': {
                                'event_info': event_info,
                                'type': message,
                                'subject': subject.name,
                                'exec_time': exec_time,
                                #'headers': list(headers.keys())
                    }})
        return Response(status=200)

    except Exception as ex:
        app.logger.error(ex, exc_info=True)
        return Response(status=201)
