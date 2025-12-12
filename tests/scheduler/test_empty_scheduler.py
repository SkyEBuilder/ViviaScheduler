import datetime as DT
from vivia_v4.task_pool import ViviaTaskPool
from vivia_v4.scheduler import ViviaScheduler


def test_scheduler_with_empty_taskpool_build_and_solve():
    start = DT.datetime(2024, 1, 1, tzinfo=DT.timezone.utc)
    end = start + DT.timedelta(days=1)
    pool = ViviaTaskPool(id=500)
    sched = ViviaScheduler(task_pool=pool, schedule_range=(start, end))

    # Build should succeed and create context with zero intervals
    sched.build_model()
    assert sched._ctx is not None, "SchedulingContext should be initialized after build_model()"
    assert len(sched._ctx.all_intervals) == 0, "Empty TaskPool should yield zero intervals in context"

    # Solve should not raise and keep zero intervals
    sched.solve()
    assert len(sched._ctx.all_intervals) == 0, "Solving empty schedule should keep zero intervals"

