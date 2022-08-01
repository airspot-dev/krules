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

from .subject import storaged_subject
from . import RuleConst as Const, ProcEventsLevel
from .providers import event_router_factory, subject_factory, configs_factory

import sys
import traceback


import logging

from .utils import get_source

logger = logging.getLogger("__core__")

from .providers import exceptions_dumpers_factory
import jsonpatch
import os
from collections.abc import Mapping


class _Rule:

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

    def _process(self, event_type, subject, payload):

        def __get_signature_info(func):
            signature = inspect.signature(func)
            return "%s(%s)" % (func.__name__, ", ".join(signature.parameters))

        def __clean(dd):
            del dd[Const.PROCESS_ID]
            del dd[Const.TYPE]
            del dd[Const.SUBJECT]
            del dd[Const.RULENAME]
            del dd[Const.SECTION]
            dd.get(Const.PAYLOAD, {}).pop("_event_info", None)
            return dd

        def __convert_simple_subject_property_proxy(v):
            if v is None:
                return v
            elif isinstance(v, bool):
                return bool(v)
            elif isinstance(v, int):
                return int(v)
            elif isinstance(v, float):
                return float(v)
            else:
                return str(v)

        def __copy_list(ll):
            dst = []
            for el in ll:
                if isinstance(el, Mapping):
                    dst.append(__copy(el))
                elif isinstance(el, (list, tuple)):
                    dst.append(__copy_list(el))
                elif inspect.isfunction(el):
                    dst.append(__get_signature_info(el))
                elif isinstance(el, (bool, int, float, str)) or el is None:
                    if isinstance(el, storaged_subject._SubjectPropertyProxy):
                        el = __convert_simple_subject_property_proxy(el)
                    dst.append(el)
                else:
                    dst.append(str(el))
            return dst

        def __copy(pp):
            cp = {}
            for k, v in pp.items():
                if isinstance(v, Mapping):
                    cp[k] = {}
                    cp[k] = __copy(v)
                elif isinstance(v, (list, tuple)):
                    cp[k] = __copy_list(v)
                elif inspect.isfunction(v):
                    cp[k] = __get_signature_info(v)
                elif isinstance(v, (bool, int, float, str)) or v is None:
                    if isinstance(v, storaged_subject._SubjectPropertyProxy):
                        v = __convert_simple_subject_property_proxy(v)
                    cp[k] = v
                else:
                    cp[k] = str(v)
            return cp

        logger.debug("process {0} for {1}".format(event_type, self.name))

        if isinstance(subject, str):
            subject = subject_factory(subject)

        from .providers import proc_events_rx_factory

        proc_events_rx = proc_events_rx_factory()  # one event for each processed rule

        process_id = str(uuid4())
        procevents_level = int(os.environ.get("PUBLISH_PROCEVENTS_LEVEL", ProcEventsLevel.DISABLED))
        last_payload = {}
        if procevents_level != ProcEventsLevel.DISABLED:
            payload_copy = __copy(payload)
            event_info = payload_copy.pop("_event_info", subject.event_info())
            res_full = {
                Const.TYPE: event_type,
                Const.SUBJECT: str(subject.name),
                Const.RULENAME: self.name,
                Const.PAYLOAD: payload_copy,
                Const.FILTERS: [],
                Const.PROCESSING: [],
                Const.GOT_ERRORS: False,
                Const.EVENT_INFO: event_info,
                Const.SOURCE: get_source()
                # DEPRECATED use event_info.get("source")
            }
            if procevents_level == ProcEventsLevel.FULL:
                last_payload = __copy(payload)

        res_in = {}
        processed_args = {}
        processed_kwargs = {}
        try:
            for _c in self._filters:
                if inspect.isclass(_c):
                    _c = _c()
                _cinst_name = _c.__class__.__name__
                if procevents_level != ProcEventsLevel.DISABLED:
                    res_in = {
                        Const.PROCESS_ID: process_id,
                        Const.TYPE: event_type,
                        Const.SUBJECT: str(subject.name),
                        Const.RULENAME: self.name,
                        Const.SECTION: Const.FILTERS,
                        Const.FUNC_NAME: _cinst_name,
                        Const.PAYLOAD: __copy(payload),
                        Const.ARGS: __copy_list(_c._processor_args),
                        Const.KWARGS: __copy(_c._processor_kwargs),
                    }
                    logger.debug("> processing: {0}".format(res_in))
                _cinst = type(_cinst_name, (_c.__class__,), {})(*_c._copy_args, **_c._copy_kwargs)
                _cinst.event_type = event_type
                _cinst.subject = subject
                _cinst.payload = payload
                _cinst.rule_name = self.name
                _cinst.router = event_router_factory()
                _cinst.configs = configs_factory()
                try:
                    processed_args = _c._get_processed_args(_cinst)
                    processed_kwargs = _c._get_processed_kwargs(_cinst)
                    res = _cinst.execute(*processed_args, **processed_kwargs)
                except TypeError as ex:
                    msg = "{} in {}: ".format(_cinst_name, self.name)
                    raise TypeError(msg + str(ex))
                if procevents_level != ProcEventsLevel.DISABLED:
                    res_out = {
                        Const.PROCESS_ID: res_in[Const.PROCESS_ID],
                        Const.TYPE: res_in[Const.TYPE],
                        Const.SUBJECT: res_in[Const.SUBJECT],
                        Const.RULENAME: res_in[Const.RULENAME],
                        Const.SECTION: res_in[Const.SECTION],
                        Const.FUNC_NAME: res_in[Const.FUNC_NAME],
                        Const.ARGS: __copy_list(processed_args),
                        Const.KWARGS: __copy(processed_kwargs),
                        Const.RETURNS: res
                    }

                    if procevents_level == ProcEventsLevel.FULL:
                        payload_copy = __copy(payload)
                        payload_patches = jsonpatch.JsonPatch.from_diff(last_payload, payload_copy).patch
                        last_payload = payload_copy
                        res_out[Const.PAYLOAD_DIFFS] = payload_patches,
                        logger.debug("< processed: {0}".format({'payload_diffs': res_out[Const.PAYLOAD_DIFFS], 'returns': res_out[Const.RETURNS]}))
                    res_full[Const.FILTERS].append(__clean(res_out))
                if not res:
                    if procevents_level != ProcEventsLevel.DISABLED:
                        res_full[Const.PASSED] = False
                        proc_events_rx.on_next(res_full)
                    return
                if procevents_level != ProcEventsLevel.DISABLED:
                    res_full[Const.PASSED] = True

            for _c in self._processing:
                if inspect.isclass(_c):
                    _c = _c()
                _cinst_name = _c.__class__.__name__
                if procevents_level != ProcEventsLevel.DISABLED:
                    res_in = {
                        Const.PROCESS_ID: process_id,
                        Const.TYPE: event_type,
                        Const.SUBJECT: str(subject.name),
                        Const.RULENAME: self.name,
                        Const.SECTION: Const.PROCESSING,
                        Const.FUNC_NAME: _cinst_name,
                        Const.PAYLOAD: __copy(payload),
                        Const.ARGS: __copy_list(_c._processor_args),
                        Const.KWARGS: __copy(_c._processor_kwargs),
                    }
                    logger.debug("> processing: {0}".format(res_in))
                #import pdb; pdb.set_trace()
                _cinst = type(_cinst_name, (_c.__class__,), {})(*_c._copy_args, **_c._copy_kwargs)
                _cinst.event_type = event_type
                _cinst.subject = subject
                _cinst.payload = payload
                _cinst.rule_name = self.name
                _cinst.router = event_router_factory()
                _cinst.configs = configs_factory()
                try:
                    processed_args = _c._get_processed_args(_cinst)
                    processed_kwargs = _c._get_processed_kwargs(_cinst)
                    res = _cinst.execute(*processed_args, **processed_kwargs)
                except TypeError as ex:
                    msg = "{} in {}: ".format(_cinst_name, self.name)
                    raise TypeError(msg + str(ex))
                if procevents_level != ProcEventsLevel.DISABLED:
                    res_out = {
                        Const.PROCESS_ID: res_in[Const.PROCESS_ID],
                        Const.TYPE: res_in[Const.TYPE],
                        Const.SUBJECT: res_in[Const.SUBJECT],
                        Const.RULENAME: res_in[Const.RULENAME],
                        Const.SECTION: res_in[Const.SECTION],
                        Const.FUNC_NAME: res_in[Const.FUNC_NAME],
                        Const.ARGS: __copy_list(processed_args),
                        Const.KWARGS: __copy(processed_kwargs),
                        Const.RETURNS: res,
                    }
                    if procevents_level == ProcEventsLevel.FULL:
                        payload_copy = __copy(payload)
                        payload_patches = jsonpatch.JsonPatch.from_diff(last_payload, payload_copy).patch
                        last_payload = payload_copy
                        res_out[Const.PAYLOAD_DIFFS] = payload_patches
                        logger.debug("< processed: {0}".format({'payload_diffs': res_out[Const.PAYLOAD_DIFFS],
                                                                'returns': res_out[Const.RETURNS]}))
                    res_full[Const.PROCESSING].append(__clean(res_out))

            if procevents_level != ProcEventsLevel.DISABLED:
                if Const.PASSED not in res_full:
                    res_full[Const.PASSED] = True
                proc_events_rx.on_next(res_full)

        except Exception as e:
            logger.error("catched exception of type {0} ({1})".format(type(e), getattr(e, 'message', str(e))))
            if proc_events_rx and procevents_level != ProcEventsLevel.DISABLED:

                type_, value_, traceback_ = sys.exc_info()
                res_out = {
                    Const.PROCESS_ID: res_in[Const.PROCESS_ID],
                    Const.TYPE: res_in[Const.TYPE],
                    Const.SUBJECT: res_in[Const.SUBJECT],
                    Const.RULENAME: res_in[Const.RULENAME],
                    Const.SECTION: res_in[Const.SECTION],
                    Const.FUNC_NAME: res_in[Const.FUNC_NAME],
                    Const.ARGS: __copy_list(processed_args),
                    Const.KWARGS: __copy(processed_kwargs),
                    Const.RETURNS: None,
                    Const.EXCEPTION: ".".join([type(e).__module__, type(e).__name__]),
                    Const.EXC_INFO: traceback.format_exception(type_, value_, traceback_),
                    Const.EXC_EXTRA_INFO: exceptions_dumpers_factory().dump(e),
                }
                if procevents_level == ProcEventsLevel.FULL:
                    payload_copy = __copy(payload)
                    payload_patches = jsonpatch.JsonPatch.from_diff(last_payload, payload_copy).patch
                    res_out[Const.PAYLOAD_DIFFS] = payload_patches

                logger.error(res_out)
                logger.debug("# unprocessed: {0}".format(res_out))
                res_full[Const.GOT_ERRORS] = True
                if Const.PASSED not in res_full:  # this happens when exception is in filters
                    res_full[Const.PASSED] = False
                res_full[res_out[Const.SECTION]].append(__clean(res_out))
                proc_events_rx.on_next(res_full)


class RuleFactory:

    @staticmethod
    def create(name: object, description: object = "", subscribe_to: object = None, data: object = {}) -> object:

        rule = _Rule(name, description)

        rule.set_filters(data.get(Const.FILTERS, []))
        rule.set_processing(data.get(Const.PROCESSING, []))
        rule.set_finally(data.get(Const.FINALLY, []))

        if isinstance(subscribe_to, str):
            subscribe_to = (subscribe_to,)
        for el in subscribe_to:
            event_router_factory().register(rule, el)
