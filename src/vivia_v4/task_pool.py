from typing import Annotated, Literal
from vivia_v4.templates import *

class Index(BaseModel):
    model_config = {
        "arbitrary_types_allowed": True,
    }
    index_type: Literal['abc']
    id: uuid.UUID = Field(description="The id of the index", default_factory=uuid.uuid4)

class GroupByName(Index):
    index_type: Literal['group_by_name'] = 'group_by_name'
    gname_id: dict[str, list[uuid.UUID]] = Field(description="The dictionary of task ids", default_factory=dict)

ALLINDEX = Annotated[GroupByName, Field(discriminator='index_type')]

class ViviaTaskPool(BaseModel):
    tasks: list[ALLTASKTEMPLATES] = Field(description="The list of tasks", default_factory=list)
    indexes: list[ALLINDEX] = Field(description="The list of indexes", default_factory=list)
    id: int
    @model_validator(mode="after")
    def initialize(self):
        for i in self.indexes:
            if i.index_type == 'group_by_name':
                return self
        g = GroupByName()
        g.gname_id["default"] = []
        self.indexes.append(g)
        return self

    def get_intervals(self, start: DT.datetime, end: DT.datetime) -> list[ScheduleInterval]:
        intervals = []
        for task in self.tasks:
            intervals += task.get_intervals(start, end)
        return intervals
    def add_task(self, task: ALLTASKTEMPLATES, group_name='default'):
        isinstance(task, Tasktemplate)
        self.tasks.append(task)
        for index in self.indexes:
            if index.index_type == 'group_by_name':
                index.gname_id[group_name].append(task.id)

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
    group_by_name = GroupByName()
    group_by_name.gname_id["test_group"] = []
    group_by_name.gname_id["test_group"].append(uuid.uuid4())
    serialized = group_by_name.model_dump_json(indent=2)
    print("Serialized GroupByName:", serialized)