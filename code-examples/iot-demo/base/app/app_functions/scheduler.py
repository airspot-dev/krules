from uuid import uuid4

from datetime import datetime, timezone

from .restapiclient import DoPostApiCall


class Schedule(DoPostApiCall):


    def _on_success(self, key, ret):
        if key is not None:
            self.subject.set(key, ret.json()["uid"], muted=True)

    def execute(self, subject: str = None, event_type: str = None, payload: dict = None,
                key: str = None, when: datetime = None, **kwargs):

        if event_type is None:
            event_type = self.event_type
        if subject is None:
            subject = self.subject.name
        if payload is None:
            payload = self.payload
        if when is None:
            when = datetime.now(timezone.utc).isoformat()
        else:
            when = when.isoformat()
        json = {
            "event_type": event_type,
            "subject": subject,
            "payload": payload,
            "origin_id": self.subject.event_info()["originid"],
            "when": when
        }
        if key is not None:
            json["uid"] = str(getattr(self.subject, key, uuid4()))

        super().execute(
            path="/scheduler/scheduled_event/",
            json=json,
            on_success=lambda ret: self._on_success(key, ret),
            raise_on_error=False
        )
