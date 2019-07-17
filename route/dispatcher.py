from krules_core.route.dispatcher import BaseDispatcher

import json

from cloudevents.sdk.event import v02
from cloudevents.sdk import marshaller
from cloudevents.sdk import converters
import uuid
from datetime import datetime

import requests

class CloudEventsDispatcher(BaseDispatcher):

    def __init__(self, dispatch_url):
        self._dispatch_url = dispatch_url

    def dispatch(self, message, subject, payload):

        _event_info = payload.pop("_event_info", getattr(subject,  "__event_info", {"origin_id": None}))

        _id = str(uuid.uuid4())
        event = (
            v02.Event()
            .SetContentType("application/json")
            .SetData(json.dumps(payload))
            .SetEventID(_id)
            .SetEventTime(datetime.utcnow().isoformat())
            .SetEventType("krules.event.{}".format(message))
            .SetExtensions({
                "subject": str(subject),
                "origin_id": _event_info.get("origin_id", _id),
                "message_source": _event_info.get("message_source"),
            })
        )

        headers, data = marshaller.NewDefaultHTTPMarshaller().ToRequest(
            event, converters.TypeStructured, json.dumps
        )

        response = requests.post(self._dispatch_url, headers=headers, data=data.getvalue())

        response.raise_for_status()
