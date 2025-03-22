from pydantic import BaseModel, Field, field_validator, ValidationInfo
from typing import Optional

class ProcessRequest(BaseModel):
    file_name: str = None
    chunk_size: Optional[int] = Field(100, gt=0, le=1000)
    overlap_size: Optional[int] = Field(20, ge=0, lt=1000)
    do_reset: Optional[int] = Field(0, ge=0, le=1)
    
    @field_validator('overlap_size')
    def overlap_less_than_chunk(cls, v: int, info: ValidationInfo) -> int:
        if info.data.get('chunk_size') is not None and v >= info.data['chunk_size']:
            raise ValueError('overlap_size must be less than chunk_size')
        return v