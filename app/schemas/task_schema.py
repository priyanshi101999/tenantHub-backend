import datetime
from pydantic import BaseModel,ConfigDict
from app.models.enums import Priority, TaskStatus
from typing import Optional

class TaskInput(BaseModel):
    title: str
    description: Optional[str]
    status: Optional[TaskStatus]
    priority: Optional[Priority]
    due_date: Optional[datetime.datetime]
    assignee_id: Optional[int]

    model_config=ConfigDict(from_attributes=True)
