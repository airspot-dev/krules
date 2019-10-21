from .. import RuleFunctionBase


class GenUUID(RuleFunctionBase):

    def execute(self, payload_dest="uuid", strip_dash=False):

        import uuid

        gen = str(uuid.uuid4())

        if strip_dash:
            gen=gen.replace("-", "")

        self.payload[payload_dest] = gen



