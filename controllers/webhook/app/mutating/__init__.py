import jsonpatch
import typing
from flask import g
from krules_core.base_functions import RuleFunctionBase

class JSONPatch(RuleFunctionBase):

    def execute(self, op, path, value=None):

        if op not in ["add", "remove", "replace"]:
            raise ValueError(f"json patch op: {op}")

        if "patch" not in self.payload["response"]:
            self.payload["response"]["patchType"] = "JSONPatch"
            self.payload["response"]["patch"] = []

        patch = {
            "op": op,
            "path": path
        }
        if op in ["add", "replace"]:
            patch.update({
                "value": value
            })

        response = g.response
        if "patch" not in response:
            response["patch"] = []
        response["patch"].append(patch)


class MakePatch(RuleFunctionBase):

    def execute(self, src: typing.Union[dict, typing.Callable], dst: typing.Union[dict, typing.Callable]):

        if "patch" not in self.payload["response"]:
            self.payload["response"]["patchType"] = "JSONPatch"
            self.payload["response"]["patch"] = []

        patch = jsonpatch.make_patch(src, dst)

        self.payload["response"]["patch"].extend(patch)
