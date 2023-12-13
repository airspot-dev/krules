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
from datetime import datetime, timezone
from pprint import pprint

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


def _callback(publish_future, exception_handler=None):
    try:
        publish_future.result(timeout=60)
    except Exception as ex:
        if exception_handler is not None:
            exception_handler(ex)
        else:
            raise


class CloudEventsDispatcher(BaseDispatcher):

    def __init__(self, project_id, topic_id, source, batch_settings=(), publisher_options=(), publisher_kwargs={}):

        self._project_id = project_id
        self._topic_id = topic_id
        self._source = source
        self._publisher = pubsub_v1.PublisherClient(
            batch_settings=batch_settings,
            publisher_options=publisher_options,
            **publisher_kwargs
        )

    def dispatch(self, event_type, subject, payload, **extra):

        if isinstance(subject, str):
            subject = subject_factory(subject)
        _event_info = subject.event_info()

        _topic_id = self._topic_id
        if "topic" in extra:
            _topic_id = extra.pop("topic")

        if callable(_topic_id):
            _topic_id = self._topic_id(subject, event_type)

        if not _topic_id:
            return

        if _topic_id.startswith("projects/"):
            topic_path = _topic_id
        else:
            topic_path = self._publisher.topic_path(self._project_id, _topic_id)

        _id = str(uuid.uuid4())
        ext_props = subject.get_ext_props()
        property_name = payload.get(PayloadConst.PROPERTY_NAME, None)
        if property_name is not None:
            ext_props.update({"propertyname": property_name})
        ext_props['originid'] = str(_event_info.get("originid", _id))
        ext_props["ce-type"] = event_type
        dataschema = extra.pop("dataschema", None)
        exception_handler = extra.pop("exception_handler", None)
        ext_props.update(extra)

        event = CloudEvent(
            id=_id,
            type=event_type,
            source=self._source,
            subject=str(subject),
            data=payload,
            time=datetime.now(timezone.utc),
            datacontenttype="application/json",
            dataschema=dataschema,
        )

        event_obj = event.model_dump(exclude_unset=True, exclude_none=True)
        event_obj["data"] = json.dumps(event_obj["data"], cls=_JSONEncoder).encode()
        event_obj["time"] = event_obj["time"].isoformat()

        future = self._publisher.publish(topic_path, **event_obj, **ext_props, contentType="text/json")
        future.add_done_callback(lambda _future: _callback(_future, exception_handler))

