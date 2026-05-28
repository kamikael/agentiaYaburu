from pydantic import BaseModel, field_validator
from typing import Optional, Any

class TestModel(BaseModel):
    messageTimestamp: Optional[int] = None

    @field_validator('messageTimestamp', mode='before')
    @classmethod
    def parse_timestamp(cls, v: Any) -> Optional[int]:
        if isinstance(v, dict):
            # protobuf type: {'low': 1779822476, 'high': 0, 'unsigned': True}
            low = v.get('low')
            high = v.get('high', 0)
            if high == 0:
                return low
            return low + (high * 4294967296)
        return v

m = TestModel(messageTimestamp={'low': 1779822476, 'high': 0, 'unsigned': True})
print("Parsed timestamp:", m.messageTimestamp)
