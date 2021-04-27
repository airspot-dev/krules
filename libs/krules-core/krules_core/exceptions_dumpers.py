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

# TODO unit tests
import inspect


class ExceptionsDumpers(object):

    def __init__(self):
        self._dumpers = {}

    def set(self, dumper):
        strcls = ""
        ex_cls = dumper.register_for
        if type(ex_cls) == str:
            strcls = ex_cls
        else:
            strcls = ".".join([ex_cls.__module__, ex_cls.__name__])
        self._dumpers[strcls] = dumper

    def dump(self, ex):
        strcls = ".".join([type(ex).__module__, type(ex).__name__])
        mro = [".".join([ex_cls.__module__, ex_cls.__name__])
               for ex_cls in inspect.getmro(ex.__class__)]
        mro.reverse()
        mro.extend([strcls])
        dumped = {}
        for cls in mro:
            if cls in self._dumpers:
                dumped.update(self._dumpers[cls].dump(ex))
        return dumped


class ExceptionDumperBase(object):

    register_for = 'builtins.Exception'

    @staticmethod
    def dump(ex):
        return {"args": ex.args}


## common exceptions dumpers

# python requests HTTPError
class RequestsHTTPErrorDumper(object):

    register_for = 'requests.exceptions.HTTPError'

    @staticmethod
    def dump(ex):
        return {
            "response_code": ex.response.status_code,
            "response_text": ex.response.text
        }




