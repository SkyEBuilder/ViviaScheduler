import datetime
from typing import Annotated, Any, Self, TypeVar, cast

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    Field,
    PlainSerializer,
    model_validator,
)

import vivia_v4.validators as VD

StartEndType = TypeVar('StartEndType')
DurationType = TypeVar('DurationType')
EndInterval = Annotated[
    list[StartEndType],
    Field(min_length=2, max_length=2),
    AfterValidator(VD.validate_interval)
]
class IntervalValidationMixin[StartEndType, DurationType](BaseModel):
    start_interval: Annotated[tuple[StartEndType, StartEndType], 
                                AfterValidator(VD.validate_interval)]
    duration_interval: Annotated[tuple[DurationType, DurationType], 
                                AfterValidator(VD.validate_interval)]
    end_interval: Annotated[tuple[StartEndType, StartEndType], 
                                AfterValidator(VD.validate_interval)]
    
    @model_validator(mode='after')
    def validate_start_end(self) -> Self:
        if self.start_interval is None or self.end_interval is None:
            return self
        VD.validate_start_end(
            cast(tuple[VD.Comparable, VD.Comparable], self.start_interval),
            cast(tuple[VD.Comparable, VD.Comparable], self.end_interval),
        )
        return self


def timedelta_validator(v) -> datetime.timedelta:
    if isinstance(v, (int, float)):
        return datetime.timedelta(seconds=v)
    return v


def timedelta_serializer(value: datetime.timedelta) -> float:
    return value.total_seconds()


TimeDelta = Annotated[
    datetime.timedelta,
    BeforeValidator(timedelta_validator),
    PlainSerializer(timedelta_serializer)
]

AwareDatetime = Annotated[
    datetime.datetime,
    AfterValidator(VD.validate_aware_datetime)
]
