import uuid
from abc import ABC, abstractmethod
from typing import Annotated, Any, Literal
from pydantic import BaseModel, Field
from vivia_v4.templates import ScheduleInterval

class Index(BaseModel, ABC):
    id: uuid.UUID = Field(description="The id of the index", default_factory=uuid.uuid4)
    
    @abstractmethod
    def build_cache(self, intervals: list[ScheduleInterval], task_map: dict[uuid.UUID, list[ScheduleInterval]]) -> Any:
        pass

class IdIndex(Index):
    index_type: Literal['id_index'] = Field(default='id_index', frozen=True)
    
    def build_cache(self, intervals: list[ScheduleInterval], task_map: dict[uuid.UUID, list[ScheduleInterval]]) -> dict[uuid.UUID, ScheduleInterval]:
        return {i.id: i for i in intervals}

class LabelIndex(Index):
    index_type: Literal['label_index'] = Field(default='label_index', frozen=True)
    
    def build_cache(self, intervals: list[ScheduleInterval], task_map: dict[uuid.UUID, list[ScheduleInterval]]) -> dict[str, list[ScheduleInterval]]:
        cache = {}
        for i in intervals:
            for label in i.labels:
                if label not in cache:
                    cache[label] = []
                cache[label].append(i)
        return cache

class GroupIndex(Index):
    index_type: Literal['group_index'] = Field(default='group_index', frozen=True)
    # Template Level: Group Name -> Task IDs
    template_groups: dict[str, list[uuid.UUID]] = Field(description="Group Name -> Task IDs", default_factory=dict)
    # Interval Level: Group Name -> Interval IDs (Precise reference)
    interval_groups: dict[str, list[uuid.UUID]] = Field(description="Group Name -> Interval IDs", default_factory=dict)

    def build_cache(self, intervals: list[ScheduleInterval], task_map: dict[uuid.UUID, list[ScheduleInterval]]) -> dict[str, list[ScheduleInterval]]:
        cache = {}
        # Template Level
        for group_name, task_ids in self.template_groups.items():
            for tid in task_ids:
                if tid in task_map:
                    if group_name not in cache:
                        cache[group_name] = []
                    cache[group_name].extend(task_map[tid])
        
        # Interval Level
        # Create temporary ID map for efficient lookup
        temp_id_map = {i.id: i for i in intervals}
        
        for group_name, interval_ids in self.interval_groups.items():
            for iid in interval_ids:
                if iid in temp_id_map:
                    if group_name not in cache:
                        cache[group_name] = []
                    cache[group_name].append(temp_id_map[iid])
                    
        # Deduplicate
        for name in cache:
             cache[name] = list({i.id: i for i in cache[name]}.values())
             
        return cache

ALLINDEX = Annotated[GroupIndex | IdIndex | LabelIndex, Field(discriminator='index_type')]
