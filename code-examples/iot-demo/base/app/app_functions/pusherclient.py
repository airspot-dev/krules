import pusher
from krules_core.base_functions import RuleFunctionBase


class WebsocketNotificationEventClass(object):

    CHEERING = "cheering"
    WARNING = "warning"
    CRITICAL = "critical"
    NORMAL = "normal"


class WebsocketDevicePublishMessage(RuleFunctionBase):

    def execute(self, data):
        pusher_client = pusher.Pusher(
            app_id=self.configs["pusher"]["credentials"]["app_id"],
            key=self.configs["pusher"]["credentials"]["key"],
            secret=self.configs["pusher"]["credentials"]["secret"],
            cluster=self.configs["pusher"]["credentials"]["cluster"],
            ssl=True
        )

        channel = self.subject.get_ext("fleet")
        event = "device-data"

        pusher_client.trigger(channel, event, data)