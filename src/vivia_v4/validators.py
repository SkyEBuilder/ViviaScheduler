import operator
import datetime
from typing import Any, TypeVar, Protocol


from collections.abc import Callable
from pydantic import BaseModel


class Comparable(Protocol):
    def __le__(self, __other: Any, /) -> bool: ...

T = TypeVar("T", bound=Comparable)

def validate_interval(t: tuple[T, T]) -> tuple[T, T]:
    if not isinstance(t, tuple) or len(t) != 2:
        raise ValueError("Interval must be a 2-tuple")
    lower, upper = t
    try:
        ok = lower <= upper
    except Exception:
        raise TypeError("Interval elements must be comparable")
    if not ok:
        raise ValueError("Lower bound must be <= upper bound")
    return t


def validate_start_end(start: tuple[Any, Any], end: tuple[Any, Any]) -> bool:
    start_lower, _ = start
    _, end_upper = end
    try:
        ok = start_lower <= end_upper
    except Exception:
        raise TypeError("Start/end interval elements must be comparable")
    if not ok:
        raise ValueError("Start lower bound must be <= end upper bound")
    return True


def make_zero_comparison_validator(mode: str) -> Callable[[int | float], int | float]:
    ops = {
        ">": operator.gt,
        ">=": operator.ge,
        "<": operator.lt,
        "<=": operator.le,
        "==": operator.eq,
        "!=": operator.ne,
    }
    if mode not in ops:
        raise ValueError(f"Unsupported comparison mode {mode!r}")
    compare = ops[mode]
    def validator(v: int | float) -> int | float:
        if not isinstance(v, (int, float)):
            raise TypeError("Value must be int or float")
        if not compare(v, 0):
            raise ValueError(f"Value {v!r} does not satisfy v {mode} 0")
        return v
    return validator


def ensure_all_or_none(model: BaseModel, field_names: list[str]) -> None:
    field_values = [getattr(model, name) for name in field_names]
    all_none = all(value is None for value in field_values)
    all_not_none = all(value is not None for value in field_values)
    if not (all_none or all_not_none):
        raise ValueError("Fields must be either all None or all set")


def validate_field_types(model: BaseModel, field_types: dict[str, type]) -> None:
    for field_name, expected_type in field_types.items():
        value = getattr(model, field_name)
        if value is not None and not isinstance(value, expected_type):
            raise TypeError(f"{field_name} must be {expected_type.__name__}, got {type(value).__name__}")


if __name__ == "__main__":
    pass