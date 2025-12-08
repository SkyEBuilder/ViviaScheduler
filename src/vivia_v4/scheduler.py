from typing import Annotated
from vivia_v4.task_pool import ViviaTaskPool
from ortools.sat.python import cp_model
from pydantic import AfterValidator, BaseModel, Field, PrivateAttr
import datetime as DT
from vivia_v4.templates import ExactDateTask, RelativePeriodItem, ScheduleInterval, FixedPeriodTask
import vivia_v4.validators as VD
import vivia_v4.model_definitions as MD
class ViviaScheduler(BaseModel):
    model_config = {
        "arbitrary_types_allowed": True,
    }
    model: cp_model.CpModel = Field(default_factory=cp_model.CpModel, exclude=True)
    solver: cp_model.CpSolver = Field(default_factory=cp_model.CpSolver, exclude=True)
    task_pool: ViviaTaskPool = Field(description="The task pool")
    schedule_range: Annotated[tuple[MD.AwareDatetime, MD.AwareDatetime], AfterValidator(VD.validate_interval)]
    _active_intervals: list[ScheduleInterval] = PrivateAttr(default_factory=list)
    unit_length: MD.TimeDelta = DT.timedelta(hours=1)
    def build_model(self):
        self._active_intervals = intervals = self.task_pool.get_intervals(*self.schedule_range)
        for x in intervals:
            x.create_cp_model_vars(self.model, self.schedule_range[0], self.schedule_range[1], self.unit_length)
        default_group = self.task_pool.indexes[0].gname_id['default']
        dgi = []
        for i in intervals:
            if i._source_task_id in default_group:
                dgi.append(i._cp_model_vars.interval)
        self.model.AddNoOverlap(dgi)
    def solve(self):
        status = self.solver.Solve(self.model)
        self.model.Maximize(sum(
            shcedule_interval.priority * (shcedule_interval._cp_model_vars.presence if shcedule_interval._cp_model_vars.presence is not None else 1) for shcedule_interval in self._active_intervals
        ))
        if status == cp_model.OPTIMAL:
            print("Optimal solution found!")
            for i in self._active_intervals:
                i.interprete_cp_model_vars(self.solver, self.schedule_range[0], self.schedule_range[1], self.unit_length)
        else:
            print("No optimal solution found.")

if __name__ == "__main__":
    utc = DT.timezone.utc
    utc_8 = DT.timezone(DT.timedelta(hours=8))
    main_datetime = DT.datetime(2008, 8, 31).replace(tzinfo=utc)
    d_interval = (main_datetime, main_datetime + DT.timedelta(hours=1))
    task_pool = ViviaTaskPool(id=6)
    test_ext_T = ExactDateTask(
        name="test",
        mandatory=True,
        priority=1,
        repeatition=1,
        start_interval=d_interval,
        end_interval=d_interval,
        duration_interval=(DT.timedelta(hours=1), DT.timedelta(hours=1))
    )
    p_item = RelativePeriodItem(
        active_index=0,
        start_interval=(DT.timedelta(hours=0), DT.timedelta(hours=1)),
        duration_interval=(DT.timedelta(hours=1), DT.timedelta(hours=1)),
        end_interval=(DT.timedelta(hours=0), DT.timedelta(hours=1))
    )
    test_fix_T = FixedPeriodTask(
        name="test",
        mandatory=True,
        priority=1,
        period_items=[p_item],
        period_unit_len=DT.timedelta(hours=1),
        period_unit_num=2,
        anchor_date=main_datetime,
        effective_interval=(main_datetime, main_datetime + DT.timedelta(days=1))
    )
    test_scheduler = ViviaScheduler(
        task_pool=task_pool,
        schedule_range=(main_datetime, main_datetime + DT.timedelta(hours=2))
    )
    task_pool.add_task(test_fix_T)
    test_scheduler.build_model()
    test_scheduler.solve()
    test_scheduler.solve()
    task_pool.save_to_json()
    new_t = task_pool.load_from_json()
    new_t.id = 3
    new_t.save_to_json()