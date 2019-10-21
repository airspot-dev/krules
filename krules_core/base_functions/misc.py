from krules_core.base_functions import RuleFunctionBase


# TODO: test

class SetSubjectPropertyToPayload(RuleFunctionBase):
    """
    Dump a subject properties to the payload
    """

    def execute(self, name, payload_dest=None, fail_if_not_exists=False, default=None):


        res = default

        try:
            prop = getattr(self.subject, name)
            value = getattr(prop, '__wrapped__', prop)
            res = value
        except AttributeError:
            if fail_if_not_exists:
                return False
        if payload_dest is None:
            payload_dest = name
        self.payload[payload_dest] = res

        return True  # can be used in filters

