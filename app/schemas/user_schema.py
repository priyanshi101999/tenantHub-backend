from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class UserInput(BaseModel):
    name: str
    email: str
    role: Optional[str] = "USER"
    workspace_id: int
    phone: str

class WorkspaceOut(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class UserOut(BaseModel):
    id: int
    name: str
    email: str
    role: str
    workspace_id: int
    email_verified: bool
    created_at: datetime
    updated_at: datetime
    workspace: WorkspaceOut

    model_config = ConfigDict(from_attributes=True) 


class User(UserOut):
    password: str
    

class InviteUser(BaseModel):
    email: str
    
class InviteUserOut(BaseModel):
    email: str
    invite_link: str





