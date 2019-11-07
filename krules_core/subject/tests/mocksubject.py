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


import wrapt

from ...subject import PayloadConst

import logging
logger = logging.getLogger(__name__)


class MockSubject(object):
    def __init__(self, name):
        logger.debug("USING FAKE SUBJECT IMPLEMETATION. JUST FOR TEST!!")
        self.name = name

        self. _props = {}

    def __str__(self):
        return "{0}".format(self.name)

    def event_info(self):
        return {}

    class _SubjectPropertyProxy(wrapt.ObjectProxy):

        _subject = None
        _name = None

        def __init__(self, _subject, name, value):
            super().__init__(value)
            self._subject = _subject
            self._name = name

        def __repr__(self):
            return self.__class__.__repr__(self.__wrapped__)

        def incr(self, value):
            try:
                float(self.__wrapped__)
            except ValueError:
                raise AttributeError("incr method not available for non numeric values")
            cur_value = self._subject._props[self._name]
            setattr(self._subject, self._name, cur_value+value)
            return getattr(self._subject, self._name)

        def decr(self, value):
            try:
                float(self.__wrapped__)
            except ValueError:
                raise AttributeError("decr method not available for non numeric values")
            cur_value = self._subject._props[self._name]
            setattr(self._subject, self._name, cur_value-value)
            return getattr(self._subject, self._name)

    def __setattr__(self, name, value):
        from ... import messages

        if name.startswith('_') or name in ['name', 'flush'] or hasattr(super(), name):  #name.startswith('_') or name in ISubject:
            return super().__setattr__(name, value)
        oldval = self._props.get(name, None)
        self._props[name] = value
        if not name.startswith("m_") and oldval != value:
            payload = {}
            payload[PayloadConst.PROPERTY_NAME] = name
            payload[PayloadConst.OLD_VALUE] = oldval
            payload[PayloadConst.VALUE] = value

            from ...providers import message_router_factory

            message_router_factory().route(messages.SUBJECT_PROPERTY_CHANGED, self.name, payload)

    def __getattr__(self, name):
        #import pdb; pdb.set_trace()
        if hasattr(super(), name):  #name.startswith('_') or name in ISubject:
            return super().__getattribute__(name)
        if name not in self._props:
            raise AttributeError
        return self._SubjectPropertyProxy(self, name, self._props[name])

    def __delattr__(self, name):
        from ... import messages

        if name in self._props:
            value = self._props[name]
            del self._props[name]
            if not name.startswith("m_"):
                payload = {}
                payload[PayloadConst.PROPERTY_NAME] = name
                payload[PayloadConst.VALUE] = value

                from ...providers import message_router_factory

                message_router_factory().route(messages.SUBJECT_PROPERTY_DELETED, self.name, payload)

        else:
            raise AttributeError

    def __len__(self):

        return len(self._props.keys())

    def __getitem__(self, item):

        return self._props[item]

    def __iter__(self):

        return iter(self._props)


    def flush(self):
        self._props = {}
        return self