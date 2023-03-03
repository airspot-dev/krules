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

import inspect
import json
import uuid
from concurrent import futures
from typing import Callable

from cloudevents.pydantic import CloudEvent
from google.cloud import pubsub_v1
from krules_core.providers import subject_factory
from krules_core.route.dispatcher import BaseDispatcher
from krules_core.subject import PayloadConst


class _JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if inspect.isfunction(obj):
            return obj.__name__
        elif isinstance(obj, object):
            return str(type(obj))
        return json.JSONEncoder.default(self, obj)


def _callback(publish_future, data):
    publish_future.result(timeout=60)


class CloudEventsDispatcher(BaseDispatcher):

    def __init__(self, project_id, topic_id, source):

        self._project_id = project_id
        self._topic_id = topic_id
        self._source = source
        self._publisher = pubsub_v1.PublisherClient()

    def dispatch(self, event_type, subject, payload, **extra):

        if isinstance(subject, str):
            subject = subject_factory(subject)
        _event_info = subject.event_info()

        _id = str(uuid.uuid4())
        ext_props = subject.get_ext_props()
        property_name = payload.get(PayloadConst.PROPERTY_NAME, None)
        if property_name is not None:
            ext_props.update({"propertyname": property_name})
        ext_props['Originid'] = str(_event_info.get("originid", _id))
        ext_props.update(extra)

        event = CloudEvent(
            id=_id,
            type=event_type,
            source=self._source,
            subject=str(subject),
            data=payload
        )

        # event.SetData(payload)

        if "topic" in extra:
            _topic_id = extra["topic"]
        else:
            _topic_id = callable(self._topic_id) and self._topic_id(subject, event_type) or self._topic_id
            if _topic_id is None:
                raise EnvironmentError("A topic must be specified or PUBSUB_SINK must be defined in environ")
        if _topic_id.startswith("projects/"):
            topic_path = _topic_id
        else:
            topic_path = self._publisher.topic_path(self._project_id, _topic_id)

        future = self._publisher.publish(topic_path, data=event.json().encode("utf-8"), **ext_props, contentType="text/json")
        future.add_done_callback(lambda _future: _future.result(timeout=60))

# class __old__CloudEventsDispatcher(BaseDispatcher):
#
#     def __init__(self, dispatch_url, source, test=False):
#         self._dispatch_url = dispatch_url
#         self._source = source
#         self._test = test
#
#     def dispatch(self, event_type, subject, payload):  # copy
#
#         if isinstance(subject, str):
#             subject = subject_factory(subject)
#         _event_info = subject.event_info()
#
#         _id = str(uuid.uuid4())
#         logging.debug("new event id: {}".format(_id))
#
#         event = v1.Event()
#         event.SetContentType('application/json')
#         event.SetEventID(_id)
#         event.SetSource(self._source)
#         event.SetSubject(str(subject))
#         event.SetEventTime(datetime.utcnow().replace(tzinfo=pytz.UTC).isoformat())
#         event.SetEventType(event_type)
#
#         # set extended properties
#         ext_props = subject.get_ext_props()
#         property_name = payload.get(PayloadConst.PROPERTY_NAME, None)
#         if property_name is not None:
#             ext_props.update({"propertyname": property_name})
#         event.SetExtensions(ext_props)
#         event.Set('Originid', str(_event_info.get("originid", _id)))
#         event.SetData(payload)
#
#         m = marshaller.NewHTTPMarshaller([binary.NewBinaryHTTPCloudEventConverter()])
#
#         headers, body = m.ToRequest(event, converters.TypeBinary, lambda x: json.dumps(x, cls=_JSONEncoder))
#
#         if "ce-datacontenttype" in headers:
#             del headers["ce-datacontenttype"]
#
#         if callable(self._dispatch_url):
#             dispatch_url = self._dispatch_url(subject, event_type)
#         else:
#             dispatch_url = self._dispatch_url
#
#         response = requests.post(dispatch_url,
#                                  headers=headers,
#                                  data=body)
#
#         response.raise_for_status()
#
#         if self._test:
#             return _id, response.status_code, headers
#         return _id
#




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
