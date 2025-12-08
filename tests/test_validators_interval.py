import pytest
import vivia_v4.validators as V

def test_validate_interval_ok():
    assert V.validate_interval((1, 2)) == (1, 2)

def test_validate_interval_equal_bounds():
    assert V.validate_interval((2, 2)) == (2, 2)

def test_validate_interval_wrong_length():
    with pytest.raises(ValueError):
        V.validate_interval((1,))

def test_validate_interval_non_comparable():
    with pytest.raises(TypeError):
        V.validate_interval((object(), object()))

def test_validate_start_end_ok():
    assert V.validate_start_end((1, 3), (2, 4)) is True

def test_validate_start_end_fail():
    with pytest.raises(ValueError):
        V.validate_start_end((5, 6), (1, 4))