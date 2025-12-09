
import pytest
import datetime as DT
import uuid
from ortools.sat.python import cp_model
from vivia_v4.templates import ExactDateTask, ScheduleInterval
from vivia_v4.constraints import NoOverlapConstraint
from vivia_v4.scheduling_context import SchedulingContext
from vivia_v4.indexes import GroupIndex
from vivia_v4.task_pool import ViviaTaskPool

def test_scheduling_context_grouping():
    # Setup
    pool = ViviaTaskPool(id=1)
    start = DT.datetime(2024, 1, 1, tzinfo=DT.timezone.utc)
    end = start + DT.timedelta(hours=5)
    
    # Task 1: Template Group "A"
    task1 = ExactDateTask(
        name="task1", mandatory=True, priority=1, repeatition=1,
        start_interval=(start, start+DT.timedelta(hours=1)),
        end_interval=(start+DT.timedelta(hours=1), start+DT.timedelta(hours=2)),
        duration_interval=(DT.timedelta(hours=1), DT.timedelta(hours=1))
    )
    pool.add_task(task1, group_name="Ignore")
    
    # Task 2: No Template Group, but will label interval as "A"
    task2 = ExactDateTask(
        name="task2", mandatory=True, priority=1, repeatition=1,
        start_interval=(start, start+DT.timedelta(hours=1)),
        end_interval=(start+DT.timedelta(hours=1), start+DT.timedelta(hours=2)),
        duration_interval=(DT.timedelta(hours=1), DT.timedelta(hours=1))
    )
    pool.add_task(task2, group_name="Ignore")

    # Task 3: No Template Group, but will add to Interval Index "A"
    task3 = ExactDateTask(
        name="task3", mandatory=True, priority=1, repeatition=1,
        start_interval=(start, start+DT.timedelta(hours=1)),
        end_interval=(start+DT.timedelta(hours=1), start+DT.timedelta(hours=2)),
        duration_interval=(DT.timedelta(hours=1), DT.timedelta(hours=1))
    )
    pool.add_task(task3, group_name="Ignore")

    # Configure Index (Template Level)
    # We need to find the existing group index or add one
    # ViviaTaskPool creates one by default.
    # But for clarity in test, we can append a new one or use the default.
    # Let's find the default one to add "A" or just create a new one.
    # Note: If multiple GroupIndexes exist, SchedulingContext merges them (as per my implementation).
    group_index = GroupIndex()
    group_index.template_groups["A"] = [task1.id]
    pool.indexes.append(group_index)

    # Get Intervals
    interval_map = pool.get_intervals(start, end)
    
    # Manually Modify for Test:
    # 1. Label Task 2's interval
    interval_map[task2.id][0].labels.add("Label_A")
    
    # 2. Add Task 3's interval to Index (Interval Level)
    t3_interval_id = interval_map[task3.id][0].id
    group_index.interval_groups["A"] = [t3_interval_id]

    # Create Context
    model = cp_model.CpModel()
    ctx = SchedulingContext(model, pool, interval_map)

    # Verify Groups
    group_a_intervals = ctx.get_intervals_by_group_name("A")
    
    # Should contain 2 intervals: 
    # - task1 (via Template Index)
    # - task3 (via Interval Index)
    assert len(group_a_intervals) == 2
    group_ids = {i.id for i in group_a_intervals}
    assert interval_map[task1.id][0].id in group_ids
    assert interval_map[task3.id][0].id in group_ids
    
    # Verify Labels
    label_a_intervals = ctx.get_intervals_by_label("Label_A")
    # Should contain 1 interval:
    # - task2 (via Label)
    assert len(label_a_intervals) == 1
    assert interval_map[task2.id][0].id == label_a_intervals[0].id
    
    # Verify Isolation: Label shouldn't be in Group, Group shouldn't be in Label
    assert interval_map[task2.id][0].id not in group_ids
    assert not ctx.get_intervals_by_group_name("Label_A")
    assert not ctx.get_intervals_by_label("A")

def test_no_overlap_constraint():
    # Setup
    pool = ViviaTaskPool(id=2)
    start = DT.datetime(2024, 1, 1, tzinfo=DT.timezone.utc)
    end = start + DT.timedelta(hours=10)
    
    # Create two overlapping tasks
    # Task 1: 00:00 - 02:00
    task1 = ExactDateTask(
        name="task1", mandatory=True, priority=1, repeatition=1,
        start_interval=(start, start),
        end_interval=(start+DT.timedelta(hours=2), start+DT.timedelta(hours=2)),
        duration_interval=(DT.timedelta(hours=2), DT.timedelta(hours=2))
    )
    
    # Task 2: 01:00 - 03:00 (Overlaps with Task 1)
    task2 = ExactDateTask(
        name="task2", mandatory=True, priority=1, repeatition=1,
        start_interval=(start+DT.timedelta(hours=1), start+DT.timedelta(hours=1)),
        end_interval=(start+DT.timedelta(hours=3), start+DT.timedelta(hours=3)),
        duration_interval=(DT.timedelta(hours=2), DT.timedelta(hours=2))
    )
    
    # Add to random group to avoid default constraint
    pool.add_task(task1, group_name="Other")
    pool.add_task(task2, group_name="Other")
    
    # Clear constraints and add custom NoOverlap
    pool.constraints = []
    # Constraint applies to both Group "ConflictGroup" and Label "ConflictLabel"
    pool.constraints.append(NoOverlapConstraint(group_name="ConflictGroup", label="ConflictLabel"))
    
    # Put Task 1 in "ConflictGroup" via Template Index
    idx = GroupIndex()
    idx.template_groups["ConflictGroup"] = [task1.id]
    pool.indexes.append(idx)
    
    # Get Intervals and Label Task 2
    interval_map = pool.get_intervals(start, end)
    interval_map[task2.id][0].labels.add("ConflictLabel")
    
    model = cp_model.CpModel()
    ctx = SchedulingContext(model, pool, interval_map)
    
    # Create vars
    for i in ctx.all_intervals:
        i.create_cp_model_vars(model, start, end, DT.timedelta(hours=1))
        
    # Apply Constraint
    constraint = pool.constraints[-1]
    constraint.apply(ctx)
    
    # Solve
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    
    # Since they overlap and both are mandatory, and we added NoOverlap covering both sources,
    # this should be INFEASIBLE.
    assert status == cp_model.INFEASIBLE

if __name__ == "__main__":
    test_scheduling_context_grouping()
    test_no_overlap_constraint()
    print("All tests passed!")
