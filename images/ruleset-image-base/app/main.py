from starlette import status
import json
from base64 import b64decode
import pydantic
import krules_env
from krules_core.providers import subject_factory, event_router_factory
from krules_core.route.router import DispatchPolicyConst
from krules_fastapi_env import KrulesApp
from datetime import datetime
import os
from fastapi import Request, Response
# from fastapi_cloudevents import CloudEvent, install_fastapi_cloudevents
from cloudevents.pydantic import CloudEvent

import io
from cloudevents.sdk.event import v1
from cloudevents.sdk import marshaller
from routers import routers
import logging

logger = logging.getLogger(__file__)


# install_fastapi_cloudevents(app)

krules_env.init()

try:
    import env

    env.init()
except ImportError:
    logger.warning("No app env defined!")


app = KrulesApp()

for router in routers:
    app.include_router(router)

event_router = event_router_factory()


@app.post("/")
async def main(request: Request, response: Response):
    start_time = datetime.now()
    try:
        dispatch_policy = os.environ.get("DISPATCH_POLICY", DispatchPolicyConst.NEVER)

        m = marshaller.NewDefaultHTTPMarshaller()
        event = m.FromRequest(v1.Event(), request.headers, io.BytesIO(json.dumps(await request.json()).encode()), lambda x: json.load(x))
        event_info = event.Properties()
        print(f"@@@@@@ {event_info}")
        event_info.update(event_info.pop("extensions", {}))
        event_data = event_info.pop("data")

        app.logger.debug("RCVR: {}".format(event_data))
        event_type = event_info.get("type")
        subject = event_info.get("subject", "sys-0")
        if event_info["source"] == os.environ.get("K_SERVICE", os.environ.get("SOURCE")):
            response.status_code = status.HTTP_201_CREATED
            return

        event_info["originid"] = event_info.get("originid", event_info.get("id"))

        app.logger.debug("subject: {}".format(subject))
        app.logger.debug("event_data: {}".format(event_data))

        if event_type == "google.cloud.pubsub.topic.v1.messagePublished":
            origin_id = event_data["message"]["messageId"]
            decoded_data = b64decode(event_data["message"]["data"]).decode()
            try:
                data = json.loads(decoded_data)
                if isinstance(data, dict):
                    try:
                        event = CloudEvent(**data)
                        event_info = event.dict(exclude_unset=True)
                        if event_info["source"] == os.environ.get("K_SERVICE", os.environ.get("SOURCE")):
                            response.status_code = status.HTTP_201_CREATED
                            return event
                        event_info.update(event_info.pop("extension", {}))
                        subject = event_info.get("subject", subject)
                        event_type = event_info.get("type")
                        event_data = event_info.pop("data") or {}
                    except pydantic.error_wrappers.ValidationError as ex:
                        event_data = data
                else:
                    event_data["message"]["data"] = data
            except json.JSONDecodeError:
                event_data["message"]["data"] = decoded_data
            event_info["originid"] = origin_id
        elif event_type == "com.google.cloud.pubsub.message":
            event_info = event_data.get("Attributes", event_info)
            event_data = event_data.get("Data", event_data)
            subject = event_info.get("subject", subject)
            event_type = event_info.get("type", event_type)

        subject = subject_factory(name=subject, event_info=event_info, event_data=event_data)

        event_data["_event_info"] = event_info  # TODO: KRUL-155

        try:
            event_router.route(
                event_type, subject, event_data,
                dispatch_policy=dispatch_policy
            )
        finally:
            pass

        exec_time = (datetime.now() - start_time).total_seconds()
        app.logger.info("Event",
                        extra={'props': {
                            'event_info': event_info,
                            'type': event_type,
                            'subject': subject.name,
                            'exec_time': exec_time,
                            # 'headers': list(headers.keys())
                        }})
        response.status_code = status.HTTP_200_OK
        return

    except Exception as ex:
        app.logger.error(ex, exc_info=True)
        response.status_code = status.HTTP_201_CREATED
        return
    # return CloudEvent(
    #     type="my.response-type.v1",
    #     data=event.data,
    #     datacontenttype=event.datacontenttype,
    # )
