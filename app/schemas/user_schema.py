from pydantic import BaseModel, ConfigDict
from datetime import datetime


class UserInput(BaseModel):
    name: str
    email: str
    role: str
    workspace_id: int

class WorkspaceOut(BaseModel):
    id: int
    name: str
    is_active: bool
    created_at: datetime

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





