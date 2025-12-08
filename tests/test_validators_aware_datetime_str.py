import datetime as DT
import pytest
import vivia_v4.validators as V

def test_validate_aware_datetime_str_ok():
    s = "2024-01-01T00:00:00+00:00"
    dt = V.validate_aware_datetime(s)
    assert isinstance(dt, DT.datetime)
    assert dt.tzinfo is not None

def test_validate_aware_datetime_str_fail_naive():
    s = "2024-01-01T00:00:00"
    with pytest.raises(ValueError):
        V.validate_aware_datetime(s)