from pydantic import Field
from vivia_v4.task_pool import ViviaTaskPool
import json
from vivia_v4.model_definitions import IntervalValidationMixin
from pydantic import BaseModel
class fuck(BaseModel):
    some_list: tuple[int, int]
    model_config = {
        "json_schema_extra": {
            "properties": {
                "some_list": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "minItems": 2,
                    "maxItems": 2,
                }
            }
    }}
schema = IntervalValidationMixin.model_json_schema()
with open('IntervalValidationMixin.json', 'w') as f:
    json.dump(schema, f, indent=2, ensure_ascii=False)
print("JSON Schema 已生成并保存到 vivia_task_pool_schema.json 文件中。")