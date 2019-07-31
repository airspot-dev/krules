import logging
import uuid
from datetime import datetime
from io import StringIO

import pycurl
from cloudevents.sdk import converters
from cloudevents.sdk import marshaller
from cloudevents.sdk.event import v02

from krules_core.route.dispatcher import BaseDispatcher


# import requests

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


        headers, data = marshaller.NewDefaultHTTPMarshaller().ToRequest(
            event, converters.TypeStructured, lambda x: x
        )

        # used pycurl to avoid thread safety issues

        c = pycurl.Curl()
        c.setopt(c.URL, self._dispatch_url)

        b = StringIO()
        c.setopt(c.POST, 1)
        c.setopt(c.HTTPHEADER, ["{}: {}".format(n, v) for n, v in headers.items()])
        c.setopt(c.WRITEFUNCTION, b.write)
        c.setopt(c.POSTFIELDS, data.read())
        c.perform()
        b.close()
        c.close()





        # url = self._dispatch_url.replace("{{message}}", message)
        # print(url)
        # #_pool.apply_async(requests.post, args=(url,), kwds={'headers': headers, 'data': data.getvalue()},
        # #                  callback=_on_success)
        # #requests.post(url, headers=headers, data=data.getvalue())
        # req = Request(url, data=data.getvalue())
        # print(req)
        # for k, v in headers.items():
        #     req.add_header(k, v)
        # req.get_method = lambda: "POST"
        # print("posting")
        # urlopen(req)
        # print("posted")

        return event
