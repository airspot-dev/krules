import typing
from krules_core.base_functions import RuleFunctionBase
from flask import g


class Deny(RuleFunctionBase):

    def execute(self, message=None, **status_kwargs):

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


