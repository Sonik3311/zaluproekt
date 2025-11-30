import json, dataclasses, pydantic
from typing import override

class EnhancedJSONEncoder(json.JSONEncoder):
    @override
    def default(self, o):
        if isinstance(o, pydantic.BaseModel):
            return o.model_dump()

        if dataclasses.is_dataclass(o):
            return dataclasses.asdict(o)
        return super().default(o)
