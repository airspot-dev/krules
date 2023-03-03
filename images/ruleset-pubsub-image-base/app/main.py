import pydantic
from starlette import status

from krules_core.providers import subject_factory
from krules_core.route.router import DispatchPolicyConst
from krules_fastapi_env import KrulesApp
from datetime import datetime
import os
from fastapi import Request, Response
import io
import json

from cloudevents.sdk.event import v1
from cloudevents.sdk import marshaller
from cloudevents.pydantic import CloudEvent
from base64 import b64decode
import krules_env
from krules_core.providers import event_router_factory

app = KrulesApp()

krules_env.init()

try:
    import env

    env.init()
except ImportError:
    app.logger.warning("No app env defined!")

event_router = event_router_factory()


@app.post("/")
async def main(request: Request, response: Response):
    start_time = datetime.now()
    try:
        dispatch_policy = os.environ.get("DISPATCH_POLICY", DispatchPolicyConst.NEVER)

        m = marshaller.NewDefaultHTTPMarshaller()
        event = m.FromRequest(v1.Event(), request.headers, io.BytesIO(json.dumps(await request.json()).encode()), lambda x: json.load(x))
        event_info = event.Properties()
        event_info.update(event_info.pop("extensions", {}))
        event_data = event_info.pop("data")

        app.logger.debug("RCVR: {}".format(event_data))
        event_type = event_info.get("type")
        subject = event_info.get("subject", "sys-0")
        if event_info["source"] == os.environ.get("K_SERVICE", os.environ.get("SOURCE")):
            response.status_code = status.HTTP_201_CREATED
            return

        event_info["originid"] = event_info.get("originid", event_info.get("id"))

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
                        event_data = event_info.pop("data")
                    except pydantic.error_wrappers.ValidationError as ex:
                        event_data = data
                else:
                    event_data["message"]["data"] = data
            except json.JSONDecodeError:
                event_data["message"]["data"] = decoded_data
            event_info["originid"] = origin_id

        app.logger.debug("subject: {}".format(subject))
        app.logger.debug("event_data: {}".format(event_data))

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
