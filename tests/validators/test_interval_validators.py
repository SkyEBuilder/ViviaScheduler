import vivia_v4.validators as V


def test_validate_interval_ok():
    assert V.validate_interval((1, 2)) == (1, 2), "validate_interval should accept non-decreasing bounds"


def test_validate_interval_equal_bounds():
    assert V.validate_interval((2, 2)) == (2, 2), "validate_interval should accept equal bounds"


def test_validate_interval_wrong_length():
    try:
        V.validate_interval((1,))
        assert False, "validate_interval should raise ValueError for wrong length"
    except ValueError:
        pass


def test_validate_interval_non_comparable():
    try:
        V.validate_interval((object(), object()))
        assert False, "validate_interval should raise TypeError for non-comparable elements"
    except TypeError:
        pass


def test_validate_start_end_ok():
    assert V.validate_start_end((1, 3), (2, 4)) is True, "validate_start_end should return True for valid ranges"


def test_validate_start_end_fail():
    try:
        V.validate_start_end((5, 6), (1, 4))
        assert False, "validate_start_end should raise ValueError when start.lower > end.upper"
    except ValueError:
        pass

