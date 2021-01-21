from datetime import datetime, timezone
from app_functions.restapiclient import DoGetApiCall
import urllib


class DispatchScheduledEvents(DoGetApiCall):

    def _dispatch_scheduled_event(self, response):
        for event in response.json():
            self.router.route("dispatch-event", self.subject, payload=event)

    def execute(self, *args, **kwargs):
        url = "/scheduler/scheduled_event?when__lte=%s" % \
              urllib.parse.quote_plus(datetime.now(timezone.utc).isoformat())

        super().execute(
            url,
            on_success=self._dispatch_scheduled_event
        )
