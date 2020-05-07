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
from uuid import uuid4

from . import RuleConst as Const
from .providers import message_router_factory, subject_factory

import sys
import traceback


import logging
logger = logging.getLogger("__core__")

from .providers import exceptions_dumpers_factory

class Rule:

    def __init__(self, name, description=""):
        self.name = name
        self.description = description,
        self._filters = []
        self._processing = []
        self._finally = []

    def set_filters(self, filters):

        assert(isinstance(filters, type([])))
        self._filters.extend(filters)

    def set_processing(self, processing):
        assert(isinstance(processing, type([])))
        self._processing.extend(processing)

    def set_finally(self, finally_):
        self._finally.extend(finally_)

    def _process(self, message, subject, payload):

        def __clean(dd):
            del dd[Const.PROCESS_ID]
            del dd[Const.MESSAGE]
            del dd[Const.SUBJECT]
            del dd[Const.RULE_NAME]
            del dd[Const.SECTION]
            return dd

        logger.debug("process {0} for {1}".format(message, self.name))

        if type(subject) == str:
            subject = subject_factory(subject)

        from .providers import results_rx_factory

        results_rx = results_rx_factory()  # one event for each processed rule

        process_id = str(uuid4())

        res_full = {
            Const.MESSAGE: message,
            Const.SUBJECT: str(subject.name),
            Const.RULE_NAME: self.name,
            Const.PAYLOAD: payload.copy(),
            Const.FILTERS: [],
            Const.PROCESSING: [],
            Const.GOT_ERRORS: False,
            #Const.EVENT_INFO: getattr(subject, "__event_info", {}),
        }

        res_in = {}
        try:
            for _c in self._filters:
                if inspect.isclass(_c):
                    _c = _c()
                _cinst_name = _c.__class__.__name__
                _cinst = type(_cinst_name, (_c.__class__,), {})()
                _cinst.message = message
                _cinst.subject = subject
                _cinst.payload = payload
                res_in = {
                    Const.PROCESS_ID: process_id,
                    Const.MESSAGE: message,
                    Const.SUBJECT: str(subject.name),
                    Const.RULE_NAME: self.name,
                    Const.SECTION: Const.FILTERS,
                    Const.FUNC_NAME: _cinst_name,
                    Const.PAYLOAD: payload.copy(),
                    Const.ARGS: _c._args,
                    Const.KWARGS: _c._kwargs,
                }
                logger.debug("> processing: {0}".format(res_in))
                try:
                    res = _cinst.execute(*_c._get_args(_cinst), **_c._get_kwargs(_cinst))
                except TypeError as ex:
                    msg = "{} in {}: ".format(_cinst_name, self.name)
                    raise TypeError(msg + str(ex))
                res_out = {
                    Const.PROCESS_ID: res_in[Const.PROCESS_ID],
                    Const.MESSAGE: res_in[Const.MESSAGE],
                    Const.SUBJECT: res_in[Const.SUBJECT],
                    Const.RULE_NAME: res_in[Const.RULE_NAME],
                    Const.SECTION: res_in[Const.SECTION],
                    Const.FUNC_NAME: res_in[Const.FUNC_NAME],
                    Const.PAYLOAD: payload.copy(),
                    Const.ARGS: res_in[Const.ARGS],
                    Const.KWARGS: res_in[Const.KWARGS],
                    Const.RETURNS: res
                }
                logger.debug("< processed: {0}".format({'payload': res_out[Const.PAYLOAD], 'returns': res_out[Const.RETURNS]}))
                res_full[Const.FILTERS].append(__clean(res_out))
                if not res:
                    res_full[Const.PROCESSED] = False
                    results_rx.on_next(res_full)
                    return

            res_full[Const.PROCESSED] = True

            for _c in self._processing:
                if inspect.isclass(_c):
                    _c = _c()
                _cinst_name = _c.__class__.__name__
                _cinst = type(_cinst_name, (_c.__class__,), {})()
                _cinst.message = message
                _cinst.subject = subject
                _cinst.payload = payload
                res_in = {
                    Const.PROCESS_ID: process_id,
                    Const.MESSAGE: message,
                    Const.SUBJECT: str(subject.name),
                    Const.RULE_NAME: self.name,
                    Const.SECTION: Const.PROCESSING,
                    Const.FUNC_NAME: _cinst_name,
                    Const.PAYLOAD: payload.copy(),
                    Const.ARGS: _c._args,
                    Const.KWARGS: _c._kwargs,
                }
                logger.debug("> processing: {0}".format(res_in))
                try:
                    res = _cinst.execute(*_c._get_args(_cinst), **_c._get_kwargs(_cinst))
                except TypeError as ex:
                    msg = "{} in {}: ".format(_cinst_name, self.name)
                    raise TypeError(msg + str(ex))
                res_out = {
                    Const.PROCESS_ID: res_in[Const.PROCESS_ID],
                    Const.MESSAGE: res_in[Const.MESSAGE],
                    Const.SUBJECT: res_in[Const.SUBJECT],
                    Const.RULE_NAME: res_in[Const.RULE_NAME],
                    Const.SECTION: res_in[Const.SECTION],
                    Const.FUNC_NAME: res_in[Const.FUNC_NAME],
                    Const.PAYLOAD: payload.copy(),
                    Const.ARGS: res_in[Const.ARGS],
                    Const.KWARGS: res_in[Const.KWARGS],
                    Const.RETURNS: res,
                }
                logger.debug("< processed: {0}".format({'payload': res_out[Const.PAYLOAD], 'returns': res_out[Const.RETURNS]}))
                res_full[Const.PROCESSING].append(__clean(res_out))

            results_rx.on_next(res_full)

        except Exception as e:
            logger.error("catched exception of type {0} ({1})".format(type(e), getattr(e, 'message', str(e))))
            if results_rx:
                type_, value_, traceback_ = sys.exc_info()
                res_out = {
                    Const.PROCESS_ID: res_in[Const.PROCESS_ID],
                    Const.MESSAGE: res_in[Const.MESSAGE],
                    Const.SUBJECT: res_in[Const.SUBJECT],
                    Const.RULE_NAME: res_in[Const.RULE_NAME],
                    Const.SECTION: res_in[Const.SECTION],
                    Const.FUNC_NAME: res_in[Const.FUNC_NAME],
                    Const.PAYLOAD: payload.copy(),
                    Const.ARGS: res_in[Const.ARGS],
                    Const.KWARGS: res_in[Const.KWARGS],
                    Const.RETURNS: None,
                    Const.EXCEPTION: ".".join([type(e).__module__, type(e).__name__]),
                    Const.EXC_INFO: traceback.format_exception(type_, value_, traceback_),
                    Const.EXC_EXTRA_INFO: exceptions_dumpers_factory().dump(e),
                }
                logger.error(res_out)
                logger.debug("# unprocessed: {0}".format(res_out))
                res_full[Const.GOT_ERRORS] = True
                res_full[res_out[Const.SECTION]].append(__clean(res_out))
                results_rx.on_next(res_full)


class RuleFactory:

    @staticmethod
    def create(rulename: object, description: object = "", subscribe_to: object = None, ruledata: object = {}) -> object:

        rule = Rule(rulename, description)

        rule.set_filters(ruledata.get(Const.FILTERS, []))
        rule.set_processing(ruledata.get(Const.PROCESSING, []))
        rule.set_finally(ruledata.get(Const.FINALLY, []))

        if isinstance(subscribe_to, str):
            subscribe_to = (subscribe_to,)
        for el in subscribe_to:
            message_router_factory().register(rule, el)
        #return message_router_factory().register(rule, subscribe_to)





