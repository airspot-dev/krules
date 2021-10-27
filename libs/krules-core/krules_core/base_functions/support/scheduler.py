from krules_core.base_functions import RuleFunctionBase
import typing
from datetime import datetime, timezone

from typing import Callable


class Schedule(RuleFunctionBase):
    """
    Allows you to program an event that will be emitted at a given time

    NOTE this is a *support* package. It needs a scheduler component concrete implementation not provided
    as part of the KRules core.

    if one or more parameters are omitted between event_type, subject and payload
    these will be taken from the current context

    If the subject_key parameter is specified,
    the event will replace the previous one with the same subject_key value for the same subject
    This same parameter can also be useful to delete a previously scheduled event
    """

    def __init__(self,
                 when: typing.Union[Callable[..., datetime], datetime] = None,
                 event_type: typing.Union[Callable[..., str], str] = None,
                 subject: typing.Union[Callable[..., str], str] = None,
                 payload: typing.Union[typing.Callable[..., dict], dict] = None,
                 subject_key: typing.Union[Callable[..., str], str] = None,
                 ):

        super().__init__(when, event_type, subject, payload, subject_key)

    def execute(self,
                when: datetime = None,
                event_type: str = None,
                subject: str = None,
                payload: dict = None,
                subject_key: str = None,
                ):

        if when is None:
            when = datetime.now(timezone.utc)
        when = when.isoformat()
        if event_type is None:
            event_type = self.event_type
        if subject is None:
            subject = self.subject
        if payload is None:
            payload = self.payload

        if "_event_info" in payload:
            del payload["_event_info"]

        self.router.route(
            event_type="krules.schedule",
            subject=self.subject,
            payload={
                "when": when,
                "event_type": event_type,
                "subject": str(subject),
                "payload": payload,
                "subject_key": subject_key
            }
        )


class Unschedule(RuleFunctionBase):
    """
    Delete a previously scheduled event
    if subject is omitted the one in the context will be used
    """

    def __init__(self,
                 subject_key: typing.Union[Callable[..., str], str] = None,
                 subject: typing.Union[Callable[..., str], str, None] = None,
                 ):

        super().__init__(subject_key, subject)

    def execute(self, subject_key: str, subject: str = None):

        if subject is None:
            subject = self.subject

        self.router.route(
            event_type="krules.unschedule",
            subject=self.subject,
            payload={
                "subject": str(subject),
                "subject_key": subject_key
            }
        )