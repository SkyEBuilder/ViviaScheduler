import datetime as DT
from vivia_v4.utils import IntervalUtil

def test_validate_interval_ok():
    assert IntervalUtil.validate_interval((1, 2)) == (1, 2)

def test_validate_interval_fail():
    try:
        IntervalUtil.validate_interval((2, 1))
        assert False
    except ValueError:
        assert True

def test_is_contained():
    outer = (DT.datetime(2024,1,1), DT.datetime(2024,1,2))
    inner = (DT.datetime(2024,1,1,12), DT.datetime(2024,1,1,18))
    assert IntervalUtil.is_contained(inner, outer)