from krules_core import RuleConst as Const
from krules_core.base_functions import *

import jsonpath_rw_ext as jp

from . import Deny

rulename = Const.RULENAME
subscribe_to = Const.SUBSCRIBE_TO
ruledata = Const.RULEDATA
filters = Const.FILTERS
processing = Const.PROCESSING


class EnvProceventsMatchHasErrors(RuleFunctionBase):

    def execute(self, value, error_dest):

        exprs = value.split(";")

        for expr in [f"$[?{expr}]" for expr in exprs]:
            try:
                jp.parse(expr)
            except Exception as ex:
                self.payload[error_dest] = f"=> {expr} => {str(ex)}"
                return True
        return False



rulesdata = [
    """
    Check PUBLISH_PROCEVENTS_LEVEL (0,1,2)
    """,
    {
        rulename: "reject-env-procevents-level",
        subscribe_to: ["validate-pod-create", "validate-pod-update"],
        ruledata: {
            filters: [
                PayloadMatchOne("$.request.object.spec.containers[0].env[?@.name='PUBLISH_PROCEVENTS_LEVEL'].value",
                                match_value=lambda value: value is not None and str(value) not in ["0", "1", "2"],
                                payload_dest="__procevents_level"),
            ],
            processing: [
                Deny(lambda payload:
                     f'PUBLISH_PROCEVENTS_LEVEL env var must be in [0, 1, 2], got {payload["__procevents_level"]}'
                     )
            ]
        }
    },
    """
    Check PUBLISH_PROCEVENTS_MATCH
    """,
    {
        rulename: "reject-env-procevents-match",
        subscribe_to: ["validate-pod-create", "validate-pod-update"],
        ruledata: {
            filters: [
                PayloadMatchOne("$.request.object.spec.containers[0].env[?@.name='PUBLISH_PROCEVENTS_MATCH'].value",
                                payload_dest="__procevents_match"),
                EnvProceventsMatchHasErrors(
                    lambda payload: payload["__procevents_match"],
                    error_dest="__match_err_expr"
                )
            ],
            processing: [
                Deny(lambda payload: f'PUBLISH_PROCEVENTS_MATCH env var has errors: {payload["__match_err_expr"]}')
            ]
        }
    }


]
