
from krules_core.base_functions import *

class PrepareSlackTextMessage(RuleFunctionBase):

    def execute(self, payload_dest="text"):

        public = self.payload["value"].startswith("https")
        if public:
            self.payload["text"] = ":unlock: new *{}* available *publicly* for *{}* at {}".format(
                self.payload["subject_match"]["app"],
                self.payload["subject_match"]["fleet"],
                self.payload["value"]
            )
        else:
            self.payload[payload_dest] = ":closed_lock_with_key: new *{}* available  *privately* for *{}* at {}".format(
                                        self.payload["subject_match"]["app"],
                                        self.payload["subject_match"]["fleet"],
                                        self.payload["value"]
            )

