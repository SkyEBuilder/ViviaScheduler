import datetime as DT
from vivia_v4.templates import FixedPeriodTask, RelativePeriodItem


def make_fixed_period_task():
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


def test_fixed_period_round_trip_initial_and_after_get():
    t = make_fixed_period_task()
    assert t.model_dump() == FixedPeriodTask.model_validate(t.model_dump()).model_dump(), "FixedPeriodTask initial round-trip mismatch"

    start = t.anchor_date
    end = t.anchor_date + DT.timedelta(days=7)
    _ = t.get_intervals(start, end)
    assert t.model_dump() == FixedPeriodTask.model_validate(t.model_dump()).model_dump(), "FixedPeriodTask post-get round-trip mismatch"


def test_fixed_period_creates_intervals_on_get():
    t = make_fixed_period_task()
    start = t.anchor_date
    end = t.anchor_date + DT.timedelta(days=7)
    assert len(t.container) == 0, "Container should be empty before get_intervals"
    intervals = t.get_intervals(start, end)
    assert len(t.container) == 1, "Exactly one period list should be created"
    assert t.container[0].time_stamp == start, "Created period time_stamp should equal period start"
    assert len(t.container[0].intervals) == 5, "Five intervals expected for active days 1..5"
    assert len(intervals) == 5, "get_intervals should return five intervals"

