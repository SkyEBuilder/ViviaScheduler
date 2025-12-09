import uuid
from typing import TYPE_CHECKING, Any
from ortools.sat.python import cp_model
from vivia_v4.templates import ScheduleInterval

if TYPE_CHECKING:
    from vivia_v4.task_pool import ViviaTaskPool

class SchedulingContext:
    def __init__(self, model: cp_model.CpModel, task_pool: "ViviaTaskPool", 
                 interval_map: dict[uuid.UUID, list[ScheduleInterval]]):
        self.model = model
        self.task_pool = task_pool
        self._interval_map = interval_map
        self._caches: dict[str, Any] = {}
        
        # Flatten intervals
        self._all_intervals = []
        for intervals in self._interval_map.values():
            self._all_intervals.extend(intervals)
            
        # Build caches
        self._build_caches()

    def _build_caches(self):
        for index in self.task_pool.indexes:
            cache = index.build_cache(self._all_intervals, self._interval_map)
            if index.index_type not in self._caches:
                self._caches[index.index_type] = cache
            else:
                # Merge logic for multiple indexes of same type
                existing = self._caches[index.index_type]
                if isinstance(existing, dict) and isinstance(cache, dict):
                     for k, v in cache.items():
                         if k not in existing:
                             existing[k] = v
                         else:
                             if isinstance(v, list):
                                 existing[k].extend(v)
                                 # Deduplicate
                                 existing[k] = list({i.id: i for i in existing[k]}.values())
                             else:
                                 # For IdIndex, just overwrite
                                 existing[k] = v

    @property
    def all_intervals(self) -> list[ScheduleInterval]:
        return self._all_intervals

    def get_intervals_by_task_id(self, task_id: uuid.UUID) -> list[ScheduleInterval]:
        return self._interval_map.get(task_id, [])

    def get_intervals_by_group_name(self, group_name: str) -> list[ScheduleInterval]:
        cache = self._caches.get('group_index', {})
        return cache.get(group_name, [])

    def get_intervals_by_label(self, label: str) -> list[ScheduleInterval]:
        cache = self._caches.get('label_index', {})
        return cache.get(label, [])
