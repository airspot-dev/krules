from flask import Flask
from flask import request
import logging
import json_logging
import os
import sys
from cloudevents.sdk import converters
from cloudevents.sdk import marshaller
from cloudevents.sdk.converters import binary
from cloudevents.sdk.event import v1
import uuid
from datetime import datetime
import pytz
import requests
import json
import socket
import krules_env
from krules_core.route.router import DispatchPolicyConst
from redis_subjects_storage import storage_impl as redis_storage_impl
from dependency_injector import providers as providers


from krules_core.providers import (
    subject_factory,
    configs_factory,
    subject_storage_factory,
    event_router_factory)

krules_env.init()

subjects_redis_storage_settings = configs_factory() \
    .get("subjects-backends") \
    .get("redis")

subject_storage_factory.override(
    providers.Factory(
        lambda name, event_info, event_data:
            redis_storage_impl.SubjectsRedisStorage(
                name,
                subjects_redis_storage_settings.get("url"),
                key_prefix=subjects_redis_storage_settings.get("key_prefix")
            )
    )
)

app = Flask("middleware")

json_logging.ENABLE_JSON_LOGGING = True
json_logging.init_flask()
json_logging.init_request_instrument(app)

logger = logging.getLogger(app.name)
logger.setLevel(int(os.environ.get("LOGGING_LEVEL", logging.DEBUG)))
logger.addHandler(logging.StreamHandler(sys.stdout))
logger.propagate = False

req_logger = logging.getLogger("flask-request-logger")
req_logger.setLevel(logging.ERROR)
req_logger.propagate = False


@app.route("/", methods=['POST'])
def main():
    if request.headers.get("authorization", "") == "Bearer %s" % os.environ.get("API_KEY"):
        if "K_SERVICE" in os.environ:
            source = os.environ["K_SERVICE"]
        elif "SERVICE" in os.environ:
            source = os.environ["SERVICE"]
        else:
            source = socket.gethostname()

        data = request.json
        subject = subject_factory("device:%s:%s" % (source, data["deviceid"]))
        subject.set_ext("phase", "running", use_cache=False)
        event_router_factory().route(
            "data-received", subject,
            {
                "receivedAt": datetime.utcnow().replace(tzinfo=pytz.UTC).isoformat(),
                "data": data,
            },
            dispatch_policy=DispatchPolicyConst.DIRECT
        )
        return "OK", 200
    else:
        return "No valid API_KEY provided", 401
