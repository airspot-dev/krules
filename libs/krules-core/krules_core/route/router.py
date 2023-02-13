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
import socket

logger = logging.getLogger("__router__")


class DispatchPolicyConst:
    DEFAULT = "default"
    ALWAYS = "always"
    NEVER = "never"
    DIRECT = "direct"


class EventRouter(object):

    def __init__(self):
        self._callables = {}

    def register(self, rule, event_type):
        logger.debug("register {0} for {1}".format(rule, event_type))
        if event_type not in self._callables:
            self._callables[event_type] = []
        self._callables[event_type].append(rule._process)

    def unregister(self, event_type):
        logger.debug("unregister event {}".format(event_type))
        count = 0
        if event_type in self._callables:
            for r in self._callables[event_type]:
                count += 1
            del self._callables[event_type]
        return count

    def unregister_all(self):
        count = 0
        types = tuple(self._callables.keys())
        for event_type in types:
            count += self.unregister(event_type)
        return count

    def route(self, event_type, subject, payload, dispatch_policy=DispatchPolicyConst.DEFAULT, **kwargs):

        if isinstance(subject, str):
            # NOTE: this should have already happened if we want to take care or event info
            from krules_core.providers import subject_factory
            subject = subject_factory(subject, event_data=payload)

        from ..providers import event_dispatcher_factory

        _callables = self._callables.get(event_type, None)

        if _callables is None:
            _callables = self._callables.get("*", None)
        else:
            _callables.extend(self._callables.get("*", []))

        #        try:
        if not dispatch_policy == DispatchPolicyConst.DIRECT:
            if _callables is not None:
                for _callable in _callables:
                    _callable(event_type, subject, payload)
        #        finally:
        #            subject.store()

        # TODO: unit test (policies)
        if dispatch_policy != DispatchPolicyConst.NEVER and _callables is None \
                and dispatch_policy == DispatchPolicyConst.DEFAULT \
                or dispatch_policy == DispatchPolicyConst.ALWAYS \
                or dispatch_policy == DispatchPolicyConst.DIRECT:
            logger.debug("dispatch {} to {} with payload {}".format(event_type, subject, payload))
            return event_dispatcher_factory().dispatch(event_type, subject, payload, **kwargs)
