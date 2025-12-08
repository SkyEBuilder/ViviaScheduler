import pytest
import vivia_v4.validators as V

def test_zero_cmp_gt_pass():
    f = V.make_zero_comparison_validator(">")
    assert f(1) == 1

def test_zero_cmp_gt_fail():
    f = V.make_zero_comparison_validator(">")
    with pytest.raises(ValueError):
        f(0)

def test_zero_cmp_type_error():
    f = V.make_zero_comparison_validator(">")
    with pytest.raises(TypeError):
        f("1")

def test_zero_cmp_unsupported():
    with pytest.raises(ValueError):
        V.make_zero_comparison_validator("BAD")