import datetime as DT
from vivia_v4.task_pool import ViviaTaskPool
from vivia_v4.templates import ExactDateTask, RelativePeriodItem, FixedPeriodTask
from vivia_v4.scheduler import ViviaScheduler

def test_scheduler_smoke():
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
