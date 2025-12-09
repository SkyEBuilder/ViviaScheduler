import datetime as DT
from pydantic.types import AwareDatetime
import uuid
from abc import ABC, abstractmethod
from typing import Annotated, Any, Literal, Self

from ortools.sat.python import cp_model
from pydantic import AwareDatetime, BaseModel, Field, PrivateAttr, model_validator

from vivia_v4.model_definitions import IntervalValidationMixin, TimeDelta
from vivia_v4.utils import IntervalUtil, Period
from vivia_v4.validators import ensure_all_or_none, validate_field_types


class RealInterval(BaseModel):
    start: AwareDatetime | None = None
    end: AwareDatetime | None = None
    
    model_config = {
        "frozen": True,  # 使实例不可变
        "validate_assignment": True
    }
    
    @property
    def duration(self) -> TimeDelta | None:
        """duration = end - start, this a property calculated, not a field"""
        if self.start is not None and self.end is not None:
            return self.end - self.start
        return None
    
    @model_validator(mode='after')
    def validate_consistency(self) -> 'RealInterval':
        ensure_all_or_none(self, ['start', 'end'])
        if self.start and self.end:
            duration = self.end - self.start
            if duration < DT.timedelta(0):
                raise ValueError("real duration can not be less than 0")
        return self
    
    def is_empty(self) -> bool:
        return self.start is None and self.end is None
    
    def set_interval(self, start: DT.datetime, end: DT.datetime) -> 'RealInterval':
        return RealInterval(start=start, end=end)
    
    def clear_interval(self) -> 'RealInterval':
        return RealInterval()
    
    def model_dump(self, **kwargs) -> dict[str, Any]:  # noqa: ANN003
        """adapted to include duration"""
        data = super().model_dump(**kwargs)
        if self.duration is not None:
            data['duration'] = self.duration
        return data


class CPModelVariables(BaseModel):
    start: cp_model.IntVar | None = None
    end: cp_model.IntVar | None = None
    presence: cp_model.IntVar | None = None
    interval: cp_model.IntervalVar | None = None
    
    model_config = {
        "arbitrary_types_allowed": True,
    }
    
    @model_validator(mode='after')
    def validate_consistency(self) -> 'CPModelVariables':
        ensure_all_or_none(self, ['start', 'end', 'presence', 'interval'])
        if self.start is not None:
            validate_field_types(self, {
                'start': cp_model.IntVar,
                'end': cp_model.IntVar,
                'presence': cp_model.IntVar,
                'interval': cp_model.IntervalVar
            })
        return self
    
    def is_empty(self) -> bool:
        return self.start is None and self.end is None and self.presence is None and self.interval is None
    
    def set_model_vars(self,start:cp_model.IntVar, end:cp_model.IntVar, presence:cp_model.IntVar,
                        interval:cp_model.IntervalVar) -> 'CPModelVariables':
        return CPModelVariables(start=start, end=end, presence=presence, interval=interval)
    
    def clear_model_vars(self) -> 'CPModelVariables':
        return CPModelVariables()

class ScheduleInterval(IntervalValidationMixin[AwareDatetime, TimeDelta]):
    name: str = Field(description="The name of the interval")
    mandatory: bool = Field(description="Whether the interval is mandatory")
    priority: int = Field(description="The priority of the interval")
    id: uuid.UUID = Field(default_factory=uuid.uuid4, description="The id of the interval")
   
    actual_interval: RealInterval = Field(default_factory=RealInterval)
    _cp_model_vars: CPModelVariables = PrivateAttr(default_factory=CPModelVariables)
    _source_task_id: uuid.UUID | None = PrivateAttr(default=None)

    def create_cp_model_vars(
        self, cp_model: cp_model.CpModel,
        schedule_start: DT.datetime, schedule_end: DT.datetime,
        unit_length: DT.timedelta) -> CPModelVariables:

        if not IntervalUtil.is_contained((self.start_interval), (schedule_start, schedule_end)):
            raise ValueError("Inproper interval, it is not contained in the schedule domain")
            pass
        from math import ceil
        def interval2unit(interval: tuple[DT.datetime, DT.datetime]) -> tuple[int, int]:
            lb = ceil((interval[0] - schedule_start) / unit_length)
            rb = (interval[1] - schedule_start) // unit_length
            return (lb, max(lb, rb))
        start = interval2unit(self.start_interval)
        end = interval2unit(self.end_interval)
        duration = ceil(self.duration_interval[0] / unit_length), self.duration_interval[1] // unit_length
        duration = (min(duration[0], duration[1]), duration[1])
        min_start, max_start = start
        min_end, max_end = end
        min_duration, max_duration = duration
        start_var = cp_model.NewIntVar(min_start, max_start, self.name + "_start_var")
        end_var = cp_model.NewIntVar(min_end, max_end, self.name + "_end_var")
        duration_var = cp_model.NewIntVar(min_duration, max_duration, self.name + "_duration_var")
        presence_var = cp_model.new_bool_var(self.name + "_presence_var")
        interval_var = cp_model.NewOptionalIntervalVar(
            start_var, duration_var, end_var, presence_var, self.name + "_interval_var"
        )
        if self.mandatory:
            cp_model.add(presence_var == 1)
        cp_model_vars = self._cp_model_vars.set_model_vars(
            start=start_var,
            end=end_var,
            presence=presence_var,
            interval=interval_var,
        )
        self._cp_model_vars = cp_model_vars
        return self._cp_model_vars

    def interprete_cp_model_vars(self, cp_solver: cp_model.CpSolver, schedule_start: DT.datetime, schedule_end: DT.datetime, unit_length: DT.timedelta):
        def unit_interval2datetime(interval):
            a = interval * unit_length
            a = schedule_start + a
            return a
        assert self._cp_model_vars.start is not None
        assert self._cp_model_vars.end is not None
        e_start = unit_interval2datetime(cp_solver.Value(self._cp_model_vars.start))
        e_end = unit_interval2datetime(cp_solver.Value(self._cp_model_vars.end))
        self.actual_interval = self.actual_interval.set_interval(e_start, e_end)
        return self.actual_interval

class constraint(BaseModel, ABC):
    @abstractmethod
    def apply_constraint2cp_model(self, model: cp_model.CpModel):
        pass

class Interval_Container(BaseModel):
    pass

class Interval_List(Interval_Container):
    intervals: list[ScheduleInterval] = Field(description="The list of intervals", default_factory=list)
    constraints: list[constraint] = Field(description="The list of constraints", default_factory=list)
    @property
    def effective_interval(self):
        all_start_L = [x.start_interval[0] for x in self.intervals]
        all_end_R = [x.end_interval[1] for x in self.intervals]
        return min(all_start_L), max(all_end_R)

class Interval_List_Timestamped(Interval_List):
    time_stamp: AwareDatetime

class Tasktemplate(BaseModel):
    template_type: Literal["exact_date", "fixed_period"] = Field(description="The type of the task template")
    name: str = Field(description="The name of the task")
    mandatory: bool = Field(description="Whether the task is mandatory")
    priority: int = Field(description="The priority of the task")
    id: uuid.UUID = Field(default_factory=uuid.uuid4, description="The id of the interval")
    container: Interval_Container

    @abstractmethod
    def get_intervals(self, start: DT.datetime, end: DT.datetime) -> list[ScheduleInterval]:
        pass

class ExactDateTask(Tasktemplate, IntervalValidationMixin[AwareDatetime, TimeDelta]):
    template_type: Literal["exact_date"] = "exact_date"
    repeatition: int = Field(description="The repeatition of the task")
    container: Interval_List = Field(description="The List of the intervals", default=Interval_List())
    @property
    def effective_interval(self) -> tuple[AwareDatetime, AwareDatetime]:
        return self.start_interval[0], self.end_interval[1]
    @model_validator(mode="after")
    def initialize(self) -> Self:
        intervals = []
        for i in range(self.repeatition):
            new_interval = ScheduleInterval(
                name=self.name + str(i),
                mandatory=self.mandatory,
                priority=self.priority,
                start_interval=self.start_interval,
                end_interval=self.end_interval,
                duration_interval=self.duration_interval,
            )
            new_interval._source_task_id = self.id
            intervals.append(new_interval)
        self.container.intervals = intervals
        return self
    def get_intervals(self, start: DT.datetime, end: DT.datetime) -> list[ScheduleInterval]:
        if IntervalUtil.is_contained(self.effective_interval, (start, end)):
            return self.container.intervals
        return []

class RelativePeriodItem(IntervalValidationMixin[TimeDelta, TimeDelta]):
    active_index: int
    
class FixedPeriodTask(Tasktemplate):
    template_type: Literal["fixed_period"] = "fixed_period"
    period_unit_len: TimeDelta = Field(description="The length of a period_unit (not the unit in scheduler)", default=DT.timedelta(days=1))
    period_unit_num: int = Field(description="The number of period_unit in a period")
    anchor_date: AwareDatetime
    effective_interval: tuple[AwareDatetime, AwareDatetime]
    period_items: list[RelativePeriodItem]
    container: list[Interval_List_Timestamped] = Field(description="The List of the intervals", default=list())
    _offset_lb: TimeDelta = PrivateAttr()
    _offset_rb: TimeDelta = PrivateAttr()
    _period: Period = PrivateAttr()
    @model_validator(mode="after")
    def validate_active_days(self):
        for item in self.period_items:
            if item.active_index < 0 or item.active_index > self.period_unit_num:
                raise ValueError("overflowing index for active_days")
        all_start = []
        all_end = []
        for item in self.period_items:
            all_start.append(item.active_index * self.period_unit_len + item.start_interval[0])
            all_end.append(item.active_index * self.period_unit_len + item.end_interval[1])
        self._offset_lb = min(all_start)
        self._offset_rb = max(all_end)
        self._period = Period(self.anchor_date, self.period_unit_num * self.period_unit_len, self.anchor_date.tzinfo)
        return self
    @property
    def datetime_stamps(self):
        return [x.time_stamp for x in self.container]
    @property
    def period_len(self):
        return self.period_unit_len * self.period_unit_num
    def _get_period_with_offset(self, target_time: AwareDatetime):
        pl, pr = self._period.get_period(target_time=target_time)
        pl += self._offset_lb
        pr = pl + self._offset_rb
        return pl, pr
    def _generate_period_intervals(self, target_time: AwareDatetime):
        pl, pb = self._period.get_period(target_time=target_time)
        ext = [x for x in self.container if x.time_stamp == pl]
        if len(ext) > 1:
            raise ValueError("重复的时间组")
        elif len(ext) == 1:
            return ext[0]
        new_interval_list: Interval_List_Timestamped = Interval_List_Timestamped(time_stamp=pl)
        for item in self.period_items:
            current_start_interval = (pl + item.start_interval[0] + item.active_index * self.period_unit_len,
                                      pl + item.start_interval[1] + item.active_index * self.period_unit_len)
            current_end_interval = (pl + item.end_interval[0] + item.active_index * self.period_unit_len,
                                      pl + item.end_interval[1] + item.active_index * self.period_unit_len)
            new_interval = ScheduleInterval(
                name=self.name + f"{current_end_interval[0]}",
                mandatory=self.mandatory,
                priority=self.priority,
                start_interval=current_start_interval,
                end_interval=current_end_interval,
                duration_interval=item.duration_interval,
            )
            new_interval._source_task_id = self.id
            new_interval_list.intervals.append(new_interval)
        self.container.append(new_interval_list)
        return new_interval_list
    def get_intervals(self, start: AwareDatetime, end: AwareDatetime) -> list[ScheduleInterval]:
        result: list[ScheduleInterval] = []
        def fuck(p):
            return IntervalUtil.is_contained(p, (start, end)) and IntervalUtil.is_contained(p, self.effective_interval)
        current_time = start
        p = self._get_period_with_offset(current_time)
        if not fuck(p):
            current_time += self.period_len
            p = self._get_period_with_offset(current_time)
        while fuck(p):
            new_interval_list = self._generate_period_intervals(current_time)
            result.extend(new_interval_list.intervals)
            current_time += self.period_len
            p = self._get_period_with_offset(current_time)
        return result
        if fuck(p):
            pass
        return super().get_intervals(start, end)
    
ALLTASKTEMPLATES = Annotated[ExactDateTask | FixedPeriodTask, Field(discriminator='template_type')]