import json, dataclasses
from typing import override

class EnhancedJSONEncoder(json.JSONEncoder):
    @override
    def default(self, o):
        if dataclasses.is_dataclass(o):
            return dataclasses.asdict(o)
        return super().default(o)
