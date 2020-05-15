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



from multiprocessing import Process

import logging
import socket

logger = logging.getLogger("__router__")

class DispatchPolicyConst:

    DEFAULT = "default"
    ALWAYS = "always"
    NEVER = "never"
    DIRECT = "direct"

from multiprocessing import Pool




class MessageRouter(object):

    def __init__(self, multiprocessing=False, wait_for_termination=False):
        self._callables = {}
        # TODO: remove multiprocessing !!!!
        self._multiproc = multiprocessing
        self._wait_for_termination = wait_for_termination

    def register(self, rule, message):
        logger.debug("register {0} for {1}".format(rule, message))
        if message not in self._callables:
            self._callables[message] = []
        self._callables[message].append(rule._process)

    def unregister(self, message):
        logger.debug("unregister message {}".format(message))
        count = 0
        if message in self._callables:
            for r in self._callables[message]:
                count += 1
            del self._callables[message]
        return count

    def unregister_all(self):
        count = 0
        messages = tuple(self._callables.keys())
        for message in messages:
            count += self.unregister(message)
        return count

    def route(self, message, subject, payload, dispatch_policy=DispatchPolicyConst.DEFAULT):

        if isinstance(subject, str):
            # NOTE: this should have already happened if we want to take care or event info
            from krules_core.providers import subject_factory
            subject = subject_factory(subject)

        from ..providers import message_dispatcher_factory

        jobs = []

        _callables = self._callables.get(message, None)

#        try:
        if not dispatch_policy == DispatchPolicyConst.DIRECT:
            if _callables is not None:
                if self._multiproc:
                    for _callable in _callables:
                        p = Process(target=_callable, args=(message, subject, payload))
                        p.start()
                        jobs.append(p)
                else:
                    for _callable in _callables:
                        _callable(message, subject, payload)

        if self._multiproc and self._wait_for_termination:
            for job in jobs:
                job.join()
#        finally:
#            subject.store()

        # TODO: unit test (policies)
        if dispatch_policy != DispatchPolicyConst.NEVER and _callables is None \
                and dispatch_policy == DispatchPolicyConst.DEFAULT \
                or dispatch_policy == DispatchPolicyConst.ALWAYS \
                or dispatch_policy == DispatchPolicyConst.DIRECT:

                logger.debug("dispatch {} to {} with payload {}".format(message, subject, payload))
                return message_dispatcher_factory().dispatch(message, subject, payload)

