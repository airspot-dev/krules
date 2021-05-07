import typing
from krules_core.base_functions import RuleFunctionBase
from flask import g


class Deny(RuleFunctionBase):

    def __init__(self, message: typing.Union[str, typing.Callable] = None, **status_kwargs):
        super().__init__(message, **status_kwargs)

    def execute(self, message=None, **status_kwargs):

        #response = self.payload["response"]
        response = g.response
        response["allowed"] = False
        if message is not None:
            status_kwargs.update({"message": message})
        if len(status_kwargs):
            if "status" not in response:
                response["status"] = {}
            response["status"].update(status_kwargs)


class Response(RuleFunctionBase):

    def execute(self, status, data):

        self.payload["response"]["status"] = status
        self.payload["response"].update(data)


