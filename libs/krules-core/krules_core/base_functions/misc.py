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


# TODO: decline to Filter/Processing
class PyCall(RuleFunctionBase):
    """
    *Execute a generic python function.
    Differently from* `Process <https://intro.krules.io/Processing.html#krules_core.base_functions.processing.Process>`_
    *, which does not allow you to interact with function result, with this function is possible to handle execution
    results whether it succeeds, using a functions which takes execution returned value as unique argument, or throws
    an exception, passing it to a chosen callable, developing a different logic for the two different cases.
    By default an exception during execution does not stop ruleset execution, by the way it is possible to
    propagate any raised exception, setting* **raise_on_error** *to True.*

    ::

        def post_to_api(url, data):
            resp = requests.post(url, data)
            resp.raise_for_status()
            return resp

        # ...

        rulesdata = [
            {
                # We register a device with a post request to an API service and we expect to receive all registration
                # info and the generated device uid.
                # If call failed we dispatch the event again, after 3 fails we raise the call exception blocking ruleset execution.
                rulename: "on-device-onboarding-post-to-api",
                subscibre_to: "device-onboarded",
                ruledata: {
                    processing: [
                        PyCall(
                            post_to_api,
                            kwargs={
                                "url": "https://my_awesome_api/devices",
                                "data": lambda payload: payload["device_info"],
                            },
                            on_success=lambda self:
                                lambda ret:
                                    self.router.route(
                                        subject="device-{}".format(ret.pop("uid"))
                                        event_type="device-posted",
                                        payload=ret
                                    ) # on success we dispatch device-posted event passing API returned data in payload
                            on_error=lambda self:
                                lambda exc:
                                    self.router.route(
                                        event_type="device-onboarded"
                                        payload={
                                            "device_info": self.payload["device_info"],
                                            "retry_count": self.payload.get("retry_count", 0) + 1 # on error we update retry_count in payload before to resend the event
                                        }
                                    )
                            payload_dest="api_response",
                            raise_on_error=lambda payload: payload.get("retry_count", 0) > 2, # if retry count is greater than 2 we block ruleset execution
                        )
                    ]
                }
            },

            # ...
            # Here we handle payload["api_response"] content whether it was successful or not

        ]

    """

    def execute(self, func, args=(), kwargs={}, on_success=None, on_error=None,
                payload_dest="pycall_returns", raise_on_error=True):
        """
        Args:
            func: Function which will be to be executed.
            args: *args that will be pass to **func**
            kwargs: **kwargs that will be pass to **func**
            on_success: Callable to handle **func** result which receive returned value as unique parameters.
            on_error: Callable to handle **func** errors, if func raises an exception this function is called receiving the raised exception.
            payload_dest: Payload's key in which func return value will be stored.
            raise_on_error: Boolean value which indicates if func exceptions will be propagated
        """

        try:
            ret = func(*args, **kwargs)
            if on_success is not None:
                on_success(ret)
            self.payload[payload_dest] = ret
        except Exception as exc:
            if on_error is not None:
                on_error(exc)
            if raise_on_error:
                raise exc

