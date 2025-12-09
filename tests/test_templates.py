def test_imports():
    import vivia_v4.templates as T
    import vivia_v4.model_definitions as M
    import vivia_v4.validators as V
    import vivia_v4.utils as U
    assert T is not None and M is not None and V is not None and U is not None
import pytest
from pydantic import AwareDatetime

def test_scheduleinterval_create_vars():
    import datetime as DT
    from ortools.sat.python import cp_model
    from vivia_v4.templates import ScheduleInterval
    from vivia_v4.model_definitions import TimeDelta
    start = DT.datetime(2024,1,1,tzinfo=DT.timezone.utc)
    end = start + DT.timedelta(hours=2)
    si = ScheduleInterval(
        name="t",
        mandatory=True,
        priority=1,
        start_interval=(start, start),
        end_interval=(end, end),
        duration_interval=(DT.timedelta(hours=2), DT.timedelta(hours=2)),
    )
    m = cp_model.CpModel()
    si.create_cp_model_vars(m, start, end, DT.timedelta(hours=1))
    assert si._cp_model_vars.interval is not None

def test_interval_validation_overflow():
    import pytest
    import datetime as DT
    from ortools.sat.python import cp_model
    from vivia_v4.templates import ScheduleInterval
    
    start_base = DT.datetime(2024, 1, 1, 0, 0, tzinfo=DT.timezone.utc)
    schedule_start = start_base
    schedule_end = start_base + DT.timedelta(hours=10)
    
    # Case 1: Interval overflows (ends after schedule_end)
    si_overflow = ScheduleInterval(
        name="overflow_task",
        mandatory=True,
        priority=1,
        start_interval=(start_base + DT.timedelta(hours=1), start_base + DT.timedelta(hours=2)),
        end_interval=(start_base + DT.timedelta(hours=11), start_base + DT.timedelta(hours=12)),
        duration_interval=(DT.timedelta(hours=9), DT.timedelta(hours=11)),
    )
    
    m = cp_model.CpModel()
    
    with pytest.raises(ValueError, match="Inproper interval"):
        si_overflow.create_cp_model_vars(m, schedule_start, schedule_end, DT.timedelta(hours=1))

def test_interval_validation_valid():
    import pytest
    import datetime as DT
    from ortools.sat.python import cp_model
    from vivia_v4.templates import ScheduleInterval
    
    start_base = DT.datetime(2024, 1, 1, 0, 0, tzinfo=DT.timezone.utc)
    schedule_start = start_base
    schedule_end = start_base + DT.timedelta(hours=10)
    
    # Case 2: Valid interval
    si_valid = ScheduleInterval(
        name="valid_task",
        mandatory=True,
        priority=1,
        start_interval=(start_base + DT.timedelta(hours=1), start_base + DT.timedelta(hours=2)),
        end_interval=(start_base + DT.timedelta(hours=8), start_base + DT.timedelta(hours=9)),
        duration_interval=(DT.timedelta(hours=6), DT.timedelta(hours=8)),
    )
    
    m = cp_model.CpModel()
    
    try:
        si_valid.create_cp_model_vars(m, schedule_start, schedule_end, DT.timedelta(hours=1))
    except ValueError:
        pytest.fail("Valid interval raised ValueError unexpectedly")