from pydantic import BaseModel
from typing import Optional

class PushRequest(BaseModel):
    do_reset: Optional[int] = 0


class SearchRequest(BaseModel):
    query: str
    limit: Optional[int] = 5

class ChatRequest(BaseModel):
    text_prompt: str