import uuid
from datetime import datetime, timezone

from krules_core import RuleConst as Const
from krules_core.base_functions import *
from krules_core.providers import subject_factory

from django.db import transaction
from krules_djangoapps_scheduler.models import ScheduledEvent

from django.utils.dateparse import parse_datetime
from django.utils import timezone


rulename = Const.RULENAME
subscribe_to = Const.SUBSCRIBE_TO
ruledata = Const.RULEDATA
filters = Const.FILTERS
processing = Const.PROCESSING


class DispatchScheduledEvent(RuleFunctionBase):

    def execute(self):

        qs = ScheduledEvent.objects.select_for_update(skip_locked=True).filter(
            when__lte=timezone.now().isoformat()
        )
        with transaction.atomic():
            for ev in qs:
                self.router.route(
                    event_type=ev.event_type,
                    subject=subject_factory(
                        ev.subject, event_info={"originid": ev.origin_id}
                    ),
                    payload=ev.payload,
                )
            qs.delete()


class ScheduleEvent(RuleFunctionBase):

    def execute(self):

        self.payload["_log"] = []

        when = parse_datetime(self.payload.get("when", timezone.now().isoformat()))
        event_type = self.payload.get("event_type")
        subject = subject_factory(self.payload.get("subject"))
        payload = self.payload.get("payload")
        subject_key = self.payload.get("subject_key")
        origin_id = self.subject.event_info().get("originid")

        if subject_key is not None:
            # try to replace the event that has already been scheduled
            #uid = getattr(subject, subject_key, None)
            #self.payload["_log"].append("found uid in subject: {}".format(uid))

            try:
                event = ScheduledEvent.objects.get(subject=subject, subject_key=subject_key)
                event.when = when
                event.event_type = event_type
                event.subject = str(subject)
                event.payload = payload
                event.origin_id = origin_id
                event.subject_key = subject_key
                event.save()

                self.payload["_log"].append("updated: {}".format(event.uid))

                return
            except ScheduledEvent.DoesNotExist:
                # event will be rescheduled
                self.payload["_log"].append("NOT FOUND")
                pass

        self.payload["_log"].append("create new object")
        ScheduledEvent.objects.create(
            when=when,
            event_type=event_type,
            subject=str(subject),
            subject_key=self.payload.get("subject_key", str(uuid.uuid4())),
            payload=payload,
            origin_id=origin_id,
        )


rulesdata = [
    """
    On tick produces scheduled events
    """,
    {
        rulename: "on-tick-do-schedules",
        subscribe_to: "scheduler.heartbeat",
        ruledata: {
            processing: [
                DispatchScheduledEvent()
            ]
        }
    },
    """
    Receive scheduled event
    """,
    {
        rulename: "schedule-event",
        subscribe_to: "krules.schedule",
        ruledata: {
            processing: [
                ScheduleEvent()
            ]
        }
    }
]
