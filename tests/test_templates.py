def test_imports():
    import vivia_v4.templates as T
    import vivia_v4.model_definitions as M
    import vivia_v4.validators as V
    import vivia_v4.utils as U
    assert T is not None and M is not None and V is not None and U is not None

def test_scheduleinterval_create_vars():
    import datetime as DT
    from ortools.sat.python import cp_model
    from vivia_v4.templates import ScheduleInterval
    from vivia_v4.model_definitions import AwareDatetime, TimeDelta
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