from datetime import datetime


class IntervalUtil:
    @staticmethod
    def validate_interval(interval):
        if interval[0] > interval[1]:
            raise ValueError('Interval left bound must be less than or equal to right bound')
        return interval

    @staticmethod
    def has_intersection(a, b):
        IntervalUtil.validate_interval(a)
        IntervalUtil.validate_interval(b)
        return a[0] <= b[1] and b[0] <= a[1]

    @staticmethod
    def intersection(a, b):
        IntervalUtil.validate_interval(a)
        IntervalUtil.validate_interval(b)
        left = max(a[0], b[0])
        right = min(a[1], b[1])
        if left > right:
            raise ValueError('No intersection')
        return (left, right)

    @staticmethod
    def is_contained(inner, outer):
        IntervalUtil.validate_interval(inner)
        IntervalUtil.validate_interval(outer)
        return outer[0] <= inner[0] and inner[1] <= outer[1]
    @staticmethod
    def is_inside(interval, target, mode: str = 'CO'):
        IntervalUtil.validate_interval(interval)
        if mode == 'CO':
            return interval[0] <= target and interval[1] > target
        else:
            raise ValueError("UNKNOWN MODE")
    
import datetime as DT
from time import timezone
def retain_date(datetime: DT.datetime) -> DT.datetime:
    if hasattr(datetime, 'tzinfo') and datetime.tzinfo is not None:
        return DT.datetime(
            datetime.year,
            datetime.month,
            datetime.day,
            tzinfo=datetime.tzinfo
        )
    else:
        return DT.datetime(
            datetime.year,
            datetime.month,
            datetime.day
        )

class Period():
    def __init__(self, anchor_date: DT.datetime, period_length: DT.timedelta) -> None:
        self.anchor_datetime = anchor_date
        self.period_length = period_length
        if self.anchor_datetime.tzinfo is None:
            raise ValueError("Anchor datetime must be timezone-aware")
        self.timezone = self.anchor_datetime.tzinfo
        self.period = (self.anchor_datetime, self.anchor_datetime + self.period_length)
        # print(self.anchor_datetime)

    def get_period(self, target_time: DT.datetime):
        target_time = target_time.astimezone(self.timezone)
        delta = (target_time - self.anchor_datetime)
        period_count = delta // self.period_length
        pivot_start_datetime = self.anchor_datetime + period_count * self.period_length
        pivot_end_datetime = pivot_start_datetime + self.period_length
        pivot = (pivot_start_datetime, pivot_end_datetime)
        if IntervalUtil.is_inside(pivot, target_time):
            self.period = pivot
            return pivot
        if target_time < pivot_start_datetime:
            prev_pivot_start = pivot_start_datetime - self.period_length
            prev_pivot_end = pivot_start_datetime
            prev_pivot = (prev_pivot_start, prev_pivot_end)
            if IntervalUtil.is_inside(prev_pivot, target_time):
                self.period = prev_pivot
                return prev_pivot
        else:
            next_pivot_start = pivot_end_datetime
            next_pivot_end = pivot_end_datetime + self.period_length
            next_pivot = (next_pivot_start, next_pivot_end)
            if IntervalUtil.is_inside(next_pivot, target_time):
                self.period = next_pivot
                return next_pivot
        raise ValueError("你的周期不知道为什么没找到")

    def next_period(self):
        start, end = self.period
        new_start = end
        new_end = new_start + self.period_length
        self.period = (new_start, new_end)
        return self.period

    def prev_period(self):
        start, end = self.period
        new_end = start
        new_start = new_end - self.period_length
        self.period = (new_start, new_end)
        return self.period

if __name__ == "__main__":
    import datetime as DT
    from datetime import timezone
    anchor = DT.datetime(2023, 10, 6, 12, 0, 0, tzinfo=timezone.utc)
    period_length = DT.timedelta(minutes=30)
    p = Period(anchor, period_length)
    print("Initial period:", p.period)
    next_p = p.next_period()
    print("Next period:", next_p)
    prev_p = p.prev_period()
    print("Previous period:", prev_p)
    target = DT.datetime(2023, 10, 27, 15, 30, 0, tzinfo=timezone.utc)
    current_period = p.get_period(target)
    print("Period for target time:", current_period)
    target_next = DT.datetime(2023, 11, 3, 15, 30, 0, tzinfo=timezone.utc)
    current_period_next = p.get_period(target_next)
    print("Period for next target time:", current_period_next)
    target_prev = DT.datetime(2023, 10, 20, 15, 30, 0, tzinfo=timezone.utc)
    current_period_prev = p.get_period(target_prev)
    print("Period for previous target time:", current_period_prev)