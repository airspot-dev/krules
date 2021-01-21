from krules_core.base_functions.misc import PyCall
from krules_core.providers import subject_factory, configs_factory
from requests import post


class SlackPublishMessage(PyCall):

    def execute(self, channel=None, text="", *args, **kwargs):
        channel = channel or "devices_channel"
        slack_settings = configs_factory().get("apps").get("slack")
        super().execute(post, args=(slack_settings[channel],), kwargs={
            "json": {
                "type": "mrkdwn",
                "text": text
            }
        })