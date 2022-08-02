from typing import Optional, NewType, List

from pydantic import BaseModel, Field, constr

from krules_core.base_functions import FilterFunction, ProcessingFunction

EventType = NewType("EventType", constr(regex="^[a-z0-9.-]+$"))


class Rule(BaseModel):

    name: str
    description: Optional[str]
    subscribe_to: EventType | List[EventType]
    filters: List[FilterFunction] = []
    processing: List[ProcessingFunction] = []

    class Config:
        arbitrary_types_allowed = True

    def dict(self, *args, **kwargs) -> dict:
        dd = super().dict(exclude_unset=True)
        dd["data"] = {}
        dd["data"]["filters"] = dd.pop("filters", [])
        dd["data"]["processing"] = dd.pop("processing", [])
        return dd



