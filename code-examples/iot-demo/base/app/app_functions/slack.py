from krules_core.base_functions import RuleFunctionBase
import requests


class SlackMessage(RuleFunctionBase):

    def execute(self, channel, text):
        requests.post(
            url=self.configs["slack"]["webhooks"][channel],
            json={
                "type": "mrkdwn",
                "text": text
            }
        )
