# Copyright 2019 The KRules Authors
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
import uuid
from datetime import datetime
import pytz
import json
import inspect


from krules_core.subject import PayloadConst

from krules_core.providers import subject_factory

from krules_core.route.dispatcher import BaseDispatcher

from cloudevents.sdk import converters
from cloudevents.sdk import marshaller
from cloudevents.sdk.converters import structured, binary
from cloudevents.sdk.event import v1

import requests


class _JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if inspect.isfunction(obj):
            return obj.__name__
        elif isinstance(obj, object):
            return str(type(obj))
        return json.JSONEncoder.default(self, obj)


class CloudEventsDispatcher(BaseDispatcher):

    def __init__(self, dispatch_url, source, test=False):
        self._dispatch_url = dispatch_url
        self._source = source
        self._test = test

    def dispatch(self, event_type, subject, payload, **kwargs):

        if isinstance(subject, str):
            subject = subject_factory(subject)
        _event_info = subject.event_info()

        _id = str(uuid.uuid4())
        logging.debug("new event id: {}".format(_id))

        event = v1.Event()
        event.SetContentType('application/json')
        event.SetEventID(_id)
        event.SetSource(self._source)
        event.SetSubject(str(subject))
        event.SetEventTime(datetime.utcnow().replace(tzinfo=pytz.UTC).isoformat())
        event.SetEventType(event_type)

        # set extended properties
        ext_props = subject.get_ext_props()
        property_name = payload.get(PayloadConst.PROPERTY_NAME, None)
        if property_name is not None:
            ext_props.update({"propertyname": property_name})
        ext_props.update(kwargs)
        event.SetExtensions(ext_props)
        event.Set('Originid', str(_event_info.get("originid", _id)))
        event.SetData(payload)

        m = marshaller.NewHTTPMarshaller([binary.NewBinaryHTTPCloudEventConverter()])

        headers, body = m.ToRequest(event, converters.TypeBinary, lambda x: json.dumps(x, cls=_JSONEncoder))

        if "ce-datacontenttype" in headers:
            del headers["ce-datacontenttype"]

        if callable(self._dispatch_url):
            dispatch_url = self._dispatch_url(subject, event_type)
        else:
            dispatch_url = self._dispatch_url

        response = requests.post(dispatch_url,
                                 headers=headers,
                                 data=body)

        response.raise_for_status()

        if self._test:
            return _id, response.status_code, headers
        return _id





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

        #return event
