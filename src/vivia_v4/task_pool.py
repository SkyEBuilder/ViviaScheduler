from typing import Annotated, Literal
import datetime as DT
import uuid
from pydantic import BaseModel, Field, model_validator
from vivia_v4.templates import ALLTASKTEMPLATES, ScheduleInterval, Tasktemplate
from vivia_v4.indexes import ALLINDEX, GroupIndex, IdIndex, LabelIndex
from vivia_v4.constraints import ALL_CONSTRAINTS, NoOverlapConstraint

class ViviaTaskPool(BaseModel):
    tasks: list[ALLTASKTEMPLATES] = Field(description="The list of tasks", default_factory=list)
    indexes: list[ALLINDEX] = Field(description="The list of indexes", default_factory=list)
    constraints: list[ALL_CONSTRAINTS] = Field(description="The list of constraints", default_factory=list)
    id: int
    @model_validator(mode="after")
    def initialize(self):
        # Ensure default NoOverlapConstraint
        has_default_constraint = False
        for c in self.constraints:
            if isinstance(c, NoOverlapConstraint) and c.group_name == 'default':
                has_default_constraint = True
                break
        if not has_default_constraint:
            self.constraints.append(NoOverlapConstraint(group_name='default'))

        # Ensure GroupIndex
        has_group_index = False
        has_id_index = False
        has_label_index = False
        
        for i in self.indexes:
            if i.index_type == 'group_index':
                has_group_index = True
            elif i.index_type == 'id_index':
                has_id_index = True
            elif i.index_type == 'label_index':
                has_label_index = True
        
        if not has_group_index:
            g = GroupIndex()
            g.template_groups["default"] = []
            self.indexes.append(g)
            
        if not has_id_index:
            self.indexes.append(IdIndex())
            
        if not has_label_index:
            self.indexes.append(LabelIndex())
            
        return self

    def get_intervals(self, start: DT.datetime, end: DT.datetime) -> dict[uuid.UUID, list[ScheduleInterval]]:
        intervals = {}
        for task in self.tasks:
            intervals[task.id] = task.get_intervals(start, end)
        return intervals
    def add_task(self, task: ALLTASKTEMPLATES, group_name='default'):
        isinstance(task, Tasktemplate)
        self.tasks.append(task)
        # Add to GroupIndex if available
        # Find the group index (first one found)
        for index in self.indexes:
            if isinstance(index, GroupIndex):
                if group_name not in index.template_groups:
                    index.template_groups[group_name] = []
                index.template_groups[group_name].append(task.id)
                break

    def remove_task(self, task: ALLTASKTEMPLATES):
        self.tasks.remove(task)

    def save_to_json(self):
        import json
        from pathlib import Path
        json_str = self.model_dump_json(indent=2)
        Path(f"{self.id}.json").write_text(json_str, encoding="utf-8")

    def load_from_json(self, filename=None):
        import json
        import os
        filename = f"{self.id}.json" if filename is None else filename
        if not os.path.exists(filename):
            raise FileNotFoundError(f"文件 {filename} 不存在")
        with open(filename, 'r', encoding='utf-8') as f:
            serializable_data = json.load(f)
        task_pool = ViviaTaskPool.model_validate(serializable_data)
        return task_pool
if __name__ == "__main__":
    task_pool = ViviaTaskPool(id=6)
    print(task_pool.model_dump_json(indent=2))
    task_pool.save_to_json()
    import uuid
    group_index = GroupIndex()
    group_index.template_groups["test_group"] = []
    group_index.template_groups["test_group"].append(uuid.uuid4())
    serialized = group_index.model_dump_json(indent=2)
    print("Serialized GroupIndex:", serialized)
