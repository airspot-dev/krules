from krules_core.route.dispatcher import BaseDispatcher

import json

from cloudevents.sdk.event import v02
from cloudevents.sdk import marshaller
from cloudevents.sdk import converters
import uuid
from datetime import datetime

import logging

from .. import _pool, _on_success
import requests


class CloudEventsDispatcher(BaseDispatcher):

    def __init__(self, dispatch_url):
        self._dispatch_url = dispatch_url

    def dispatch(self, message, subject, payload):

        _event_info = payload.pop("_event_info", getattr(subject,  "__event_info", {"origin_id": None}))

        _id = str(uuid.uuid4())
        logging.debug("new event id: {}".format(_id))
        event = (
            v02.Event()
            .SetContentType("application/json")
            .SetData(payload)
            .SetEventID(_id)
            .SetEventTime(datetime.utcnow().isoformat())
            .SetEventType("krules.event.{}".format(message))
            .SetSource(_event_info.get("message_source"))
            .SetExtensions({
                "subject": str(subject),
                "origin_id": _event_info.get("origin_id", _id),
            })
        )


        #import pdb; pdb.set_trace()
        headers, data = marshaller.NewDefaultHTTPMarshaller().ToRequest(
            event, converters.TypeStructured, lambda x: x
        )

        _pool.apply_async(requests.post, args=(self._dispatch_url,), kwds={'headers': headers, 'data': data.getvalue()},
                          callback=_on_success)

        #response = requests.post(self._dispatch_url, headers=headers, data=data.getvalue())

        #response.raise_for_status()

        return event
