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
from krules_core.base_functions import RuleFunctionBase


class PyCall(RuleFunctionBase):
    """
    Execute a generic python function
    """

    def execute(self, func, args=(), kwargs={}, on_success=None, on_error=None,
                payload_dest="pycall_returns", raise_on_error=True):
        """
        Args:
            func: function to call
            args: function *args
            kwargs: function **kwargs
            on_success: function receiving (self, func_return_value)
            on_error: callable, if func raises an exception this function is called receiving (self, exception)
            payload_dest: key in payload storing func return value
            raise_on_error: if False and func produce an exception, it is not raised
        """

        try:
            ret = func(*args, **kwargs)
            if on_success is not None:
                on_success(self, ret)
            self.payload[payload_dest] = ret
        except Exception as exc:
            if on_error is not None:
                on_error(self, exc)
            if raise_on_error:
                raise exc

