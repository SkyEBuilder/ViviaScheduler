from typing import Annotated
from vivia_v4.task_pool import ViviaTaskPool
from ortools.sat.python import cp_model
from pydantic import AfterValidator, BaseModel, Field, PrivateAttr, AwareDatetime
import datetime as DT
from vivia_v4.templates import ExactDateTask, RelativePeriodItem, ScheduleInterval, FixedPeriodTask
from vivia_v4.scheduling_context import SchedulingContext
import vivia_v4.validators as VD
import vivia_v4.model_definitions as MD
class ViviaScheduler(BaseModel):
    model_config = {
        "arbitrary_types_allowed": True,
    }
    model: cp_model.CpModel = Field(default_factory=cp_model.CpModel, exclude=True)
    solver: cp_model.CpSolver = Field(default_factory=cp_model.CpSolver, exclude=True)
    task_pool: ViviaTaskPool = Field(description="The task pool")
    schedule_range: Annotated[tuple[AwareDatetime, AwareDatetime], AfterValidator(VD.validate_interval)]
    _ctx: SchedulingContext | None = PrivateAttr(default=None)
    unit_length: MD.TimeDelta = DT.timedelta(hours=1)

    def build_model(self):
        # 1. Get intervals map from TaskPool
        interval_map = self.task_pool.get_intervals(*self.schedule_range)
        
        # 2. Initialize SchedulingContext (builds indexes automatically)
        self._ctx = SchedulingContext(model=self.model, task_pool=self.task_pool, interval_map=interval_map)
        
        # 3. Create CP variables for all intervals
        for interval in self._ctx.all_intervals:
            interval.create_cp_model_vars(self.model, self.schedule_range[0], self.schedule_range[1], self.unit_length)
        
        # 4. Apply all constraints
        for constraint in self.task_pool.constraints:
            constraint.apply(self._ctx)

    def solve(self):
        if self._ctx is None:
            raise ValueError("Model not built. Call build_model() first.")
            
        # Maximize priority * presence
        self.model.Maximize(sum(
            shcedule_interval.priority * (shcedule_interval._cp_model_vars.presence if shcedule_interval._cp_model_vars.presence is not None else 1) 
            for shcedule_interval in self._ctx.all_intervals
        ))
        
        status = self.solver.Solve(self.model)
        
        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            msg = "Optimal solution found!" if status == cp_model.OPTIMAL else "Feasible solution found!"
            print(msg)
            for i in self._ctx.all_intervals:
                i.interprete_cp_model_vars(self.solver, self.schedule_range[0], self.schedule_range[1], self.unit_length)
        else:
            print("No feasible solution found.")
