import datetime as DT
from vivia_v4.task_pool import ViviaTaskPool
from vivia_v4.scheduler import ViviaScheduler
from vivia_v4.templates import ExactDateTask


def make_exact_task(repeatition: int, mandatory: bool):
    anchor = DT.datetime(2007, 8, 31, 0, 0, tzinfo=DT.timezone.utc)
    end = anchor + DT.timedelta(days=7)
    return ExactDateTask(
        name="exact_sched",
        mandatory=mandatory,
        priority=1,
        repeatition=repeatition,
        # Allow feasible scheduling: start in [anchor, end-12h], end in [anchor+12h, end]
        start_interval=(anchor, end - DT.timedelta(hours=12)),
        end_interval=(anchor + DT.timedelta(hours=12), end),
        duration_interval=(DT.timedelta(hours=12), DT.timedelta(hours=12)),
    )


def test_exact_four_intervals_solve_all():
    pool = ViviaTaskPool(id=600)
    t = make_exact_task(4, mandatory=True)
    pool.add_task(t)
    start = DT.datetime(2007, 8, 31, 0, 0, tzinfo=DT.timezone.utc)
    end = start + DT.timedelta(days=7)
    sched = ViviaScheduler(task_pool=pool, schedule_range=(start, end))
    sched.build_model()
    sched.solve()
    assert len(t.container.intervals) == 4, "ExactDateTask should have 4 intervals in container"
    assert all(not i.actual_interval.is_empty() for i in t.container.intervals), "All 4 intervals should be scheduled (non-empty actual_interval)"


def test_exact_fifteen_intervals_one_unassigned():
    pool = ViviaTaskPool(id=601)
    t = make_exact_task(15, mandatory=False)
    pool.add_task(t)
    start = DT.datetime(2007, 8, 31, 0, 0, tzinfo=DT.timezone.utc)
    end = start + DT.timedelta(days=7)
    sched = ViviaScheduler(task_pool=pool, schedule_range=(start, end))
    sched.build_model()
    sched.solve()
    empties = sum(1 for i in t.container.intervals if i.actual_interval.is_empty())
    assert empties == 1, "Exactly one interval should be unassigned (empty actual_interval) in 168h window for 15x12h"
