import datetime
from pydantic import BaseModel,ConfigDict
from app.models.enums import Priority, TaskStatus
from typing import Optional

class TaskInput(BaseModel):
    title: str
    description: Optional[str] = None
    status: Optional[TaskStatus] = TaskStatus.TODO
    priority: Optional[Priority] = Priority.MEDIUM
    due_date: Optional[datetime.datetime] = None
    assignee_id: Optional[int] = None

    model_config=ConfigDict(from_attributes=True)

class TaskOut(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    status: TaskStatus
    priority: Priority
    due_date: Optional[datetime.datetime] = None
    assignee_id: Optional[int] = None
    created_by: Optional[int] = None
    workspace_id: int
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config=ConfigDict(from_attributes=True)

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[Priority] = None
    due_date: Optional[datetime.datetime] = None
    assignee_id: Optional[int] = None

    model_config=ConfigDict(from_attributes=True)

class AttachmentOut(BaseModel):
    id: int
    file_name: str
    file_path: str
    task_id: int

    model_config=ConfigDict(from_attributes=True)
