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
from io import StringIO, BytesIO
import json

import pycurl

from krules_core.subject import PayloadConst

from krules_core.providers import subject_factory

from krules_core.route.dispatcher import BaseDispatcher


# import requests

class CloudEventsDispatcher(BaseDispatcher):

    def __init__(self, dispatch_url, source, test=False):
        self._dispatch_url = dispatch_url
        self._source = source
        self._test = test

    def dispatch(self, message, subject, payload):

        if type(subject) == str:
            subject = subject_factory(subject)
        _event_info = subject.event_info()

        _id = str(uuid.uuid4())
        logging.debug("new event id: {}".format(_id))

        headers = {
            'Content-Type': 'application/json',
            'Ce-Specversion': '0.3',
            'Ce-Id': _id,
            'Ce-Originid': str(_event_info.get("Originid", _id)),
            'Ce-Source': self._source,
            'Ce-Subject': str(subject),
            'Ce-Time': datetime.utcnow().isoformat(),
            'Ce-Type': message,
            'Accept-Encoding': 'gzip'
        }

        # set extended properties
        ext_props = subject.get_ext_props()
        property_name = payload.get(PayloadConst.PROPERTY_NAME, None)
        if property_name is not None:
            ext_props.append(("propertyname", property_name))
        for prop, value in ext_props:
            headers["Ce-{}".format(prop.capitalize())] = value


        # if payload contains a property_name attribute it is set as ce extension
        # property_name = payload.get(PayloadConst.PROPERTY_NAME, None)
        # if property_name is not None:
        #     headers["Ce-Propertyname"] = property_name

        # used pycurl to avoid thread safety issues
        c = pycurl.Curl()
        c.setopt(c.URL, self._dispatch_url)

        b = BytesIO()
        c.setopt(c.POST, 1)
        c.setopt(c.HTTPHEADER, ["{}: {}".format(n, v) for n, v in headers.items()])
        c.setopt(c.WRITEFUNCTION, b.write)
        #c.setopt(c.POSTFIELDS, data.read())
        c.setopt(c.POSTFIELDS, json.dumps(payload))
        c.perform()
        response_code = c.getinfo(pycurl.RESPONSE_CODE)
        b.close()
        c.close()

        if self._test:
            return _id, response_code, headers
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
