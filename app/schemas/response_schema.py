from pydantic import BaseModel
from typing import Optional, Any

class APIResponse(BaseModel):
    message: str
    data: Optional[Any] = None
    status: int