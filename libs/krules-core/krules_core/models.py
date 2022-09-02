from typing import Optional, NewType, List

from pydantic import BaseModel, Field, constr

from krules_core.arg_processors import BaseArgProcessor
from krules_core.base_functions import FilterFunction, ProcessingFunction, Filter, Process

EventType = NewType("EventType", constr(regex="^[a-z0-9.-]+$"))


class Rule(BaseModel):

    name: str
    description: Optional[str]
    subscribe_to: Optional[EventType | List[EventType]]
    filters: List[FilterFunction | BaseArgProcessor] = []
    processing: List[ProcessingFunction | BaseArgProcessor] = []

    class Config:
        arbitrary_types_allowed = True

    def dict(self, *args, **kwargs) -> dict:
        dd = super().dict(exclude_unset=True)
        dd["data"] = {}
        filters = dd.pop("filters", [])
        for idx, f in enumerate(filters):
            if isinstance(f, BaseArgProcessor):
                filters[idx] = Filter(f)
        processing = dd.pop("processing", [])
        for idx, f in enumerate(processing):
            if isinstance(f, BaseArgProcessor):
                processing[idx] = Process(f)
        dd["data"]["filters"] = filters
        dd["data"]["processing"] = processing
        return dd



