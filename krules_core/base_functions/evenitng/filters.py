from krules_core.base_functions import RuleFunctionBase


class IsInternalEvent(RuleFunctionBase):

    def execute(self):

        _event_info = self.payload.get("_event_info", {})

        if "message_source" in _event_info:
            return False

        return True
