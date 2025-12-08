import datetime as DT
import vivia_v4.validators as V

def test_validate_aware_datetime_ok():
    dt = DT.datetime(2024,1,1,tzinfo=DT.timezone.utc)
    assert V.validate_aware_datetime(dt) == dt

def test_validate_aware_datetime_fail():
    try:
        V.validate_aware_datetime(DT.datetime(2024,1,1))
        assert False
    except ValueError:
        assert True