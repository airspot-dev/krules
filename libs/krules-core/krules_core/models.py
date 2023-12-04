from typing import Optional, NewType, List

from krules_core.arg_processors import BaseArgProcessor
from krules_core.base_functions.filters import FilterFunction, Filter
from krules_core.base_functions.processing import ProcessingFunction, Process
from pydantic import BaseModel, constr

EventType = NewType("EventType", constr(pattern="^[a-zA-Z0-9_.-]+$"))


class Rule(BaseModel):

    name: str
    description: Optional[str] = "",
    subscribe_to: Optional[EventType | List[EventType]] = ["*"]
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



