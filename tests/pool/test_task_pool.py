import datetime as DT
from vivia_v4.task_pool import ViviaTaskPool
from vivia_v4.templates import ExactDateTask, FixedPeriodTask, RelativePeriodItem
from vivia_v4.constraints import NoOverlapConstraint


def test_empty_taskpool_round_trip():
    pool = ViviaTaskPool(id=100)
    assert pool.model_dump() == ViviaTaskPool.model_validate(pool.model_dump()).model_dump(), "Empty TaskPool round-trip mismatch"


def test_empty_taskpool_has_default_constraint():
    pool = ViviaTaskPool(id=101)
    assert any(isinstance(c, NoOverlapConstraint) and c.group_name == 'default' for c in pool.constraints), "Default NoOverlapConstraint('default') should exist"


def make_exact_date_task_for_week():
    anchor = DT.datetime(2007, 8, 31, 0, 0, tzinfo=DT.timezone.utc)
    end = anchor + DT.timedelta(days=7)
    return ExactDateTask(
        name="exact_week",
        mandatory=False,
        priority=1,
        repeatition=15,
        start_interval=(anchor, anchor),
        end_interval=(end, end),
        duration_interval=(DT.timedelta(hours=12), DT.timedelta(hours=12)),
    )


def test_taskpool_exact_date_round_trip_before_get_and_after_get_and_oob():
    pool = ViviaTaskPool(id=200)
    t = make_exact_date_task_for_week()
    pool.add_task(t)

    assert pool.model_dump() == ViviaTaskPool.model_validate(pool.model_dump()).model_dump(), "TaskPool+ExactDate round-trip before get mismatch"

    anchor = DT.datetime(2007, 8, 31, 0, 0, tzinfo=DT.timezone.utc)
    end = anchor + DT.timedelta(days=7)
    interval_map = pool.get_intervals(anchor, end)
    assert t.id in interval_map, "ExactDateTask id must exist in interval_map"
    assert len(interval_map[t.id]) == 15, "ExactDateTask should return all 15 intervals when window fully contains"

    assert pool.model_dump() == ViviaTaskPool.model_validate(pool.model_dump()).model_dump(), "TaskPool+ExactDate round-trip after get mismatch"

    out_task = ExactDateTask(
        name="exact_out", mandatory=False, priority=1, repeatition=10,
        start_interval=(anchor + DT.timedelta(days=14), anchor + DT.timedelta(days=14)),
        end_interval=(anchor + DT.timedelta(days=15), anchor + DT.timedelta(days=15)),
        duration_interval=(DT.timedelta(hours=12), DT.timedelta(hours=12)),
    )
    pool.add_task(out_task)
    interval_map2 = pool.get_intervals(anchor, end)
    assert len(interval_map2[t.id]) == 15, "Original ExactDateTask must still return 15 intervals"
    assert len(interval_map2[out_task.id]) == 0, "Out-of-bounds ExactDateTask must return 0 intervals"


def make_fixed_period_task_for_week():
    anchor = DT.datetime(2007, 8, 31, 0, 0, tzinfo=DT.timezone.utc)
    period_len = DT.timedelta(days=1)
    period_num = 7
    effective = (anchor, anchor + DT.timedelta(days=7))
    items: list[RelativePeriodItem] = []
    for idx in range(1, 6):
        items.append(
            RelativePeriodItem(
                active_index=idx,
                start_interval=(DT.timedelta(hours=8), DT.timedelta(hours=8)),
                end_interval=(DT.timedelta(hours=18), DT.timedelta(hours=18)),
                duration_interval=(DT.timedelta(hours=10), DT.timedelta(hours=10)),
            )
        )
    return FixedPeriodTask(
        name="fixed_week",
        mandatory=True,
        priority=1,
        period_unit_len=period_len,
        period_unit_num=period_num,
        anchor_date=anchor,
        effective_interval=effective,
        period_items=items,
    )


def test_taskpool_fixed_period_round_trip_before_get_and_after_get():
    pool = ViviaTaskPool(id=300)
    t = make_fixed_period_task_for_week()
    pool.add_task(t)

    assert pool.model_dump() == ViviaTaskPool.model_validate(pool.model_dump()).model_dump(), "TaskPool+FixedPeriod round-trip before get mismatch"

    anchor = DT.datetime(2007, 8, 31, 0, 0, tzinfo=DT.timezone.utc)
    end = anchor + DT.timedelta(days=7)
    interval_map = pool.get_intervals(anchor, end)
    assert t.id in interval_map, "FixedPeriodTask id must exist in interval_map"
    assert len(interval_map[t.id]) == 5, "FixedPeriodTask should return 5 intervals for active days 1..5"

    assert pool.model_dump() == ViviaTaskPool.model_validate(pool.model_dump()).model_dump(), "TaskPool+FixedPeriod round-trip after get mismatch"

