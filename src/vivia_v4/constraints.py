from abc import ABC, abstractmethod
from typing import Annotated, Literal, TYPE_CHECKING
from pydantic import BaseModel, Field, model_validator
from ortools.sat.python import cp_model

if TYPE_CHECKING:
    from vivia_v4.scheduling_context import SchedulingContext

class BaseConstraint(BaseModel, ABC):
    @abstractmethod
    def apply(self, ctx: "SchedulingContext"):
        pass

class NoOverlapConstraint(BaseConstraint):
    constraint_type: Literal["no_overlap"] = Field(default="no_overlap", frozen=True)
    group_name: str | None = None
    label: str | None = None
    
    @model_validator(mode='after')
    def validate_target(self):
        if self.group_name is None and self.label is None:
            raise ValueError("Either group_name or label must be provided")
        return self
    
    def apply(self, ctx: "SchedulingContext"):
        intervals = []
        if self.group_name:
            intervals.extend(ctx.get_intervals_by_group_name(self.group_name))
        if self.label:
            intervals.extend(ctx.get_intervals_by_label(self.label))
            
        # Deduplicate if both group and label provided overlapping results
        if self.group_name and self.label:
            intervals = list({i.id: i for i in intervals}.values())
            
        cp_intervals = [i._cp_model_vars.interval for i in intervals if i._cp_model_vars.interval]
        if cp_intervals:
            ctx.model.AddNoOverlap(cp_intervals)

ALL_CONSTRAINTS = Annotated[NoOverlapConstraint, Field(discriminator='constraint_type')]

class constraint(BaseModel, ABC):
    @abstractmethod
    def apply_constraint2cp_model(self, model: cp_model.CpModel):
        pass
