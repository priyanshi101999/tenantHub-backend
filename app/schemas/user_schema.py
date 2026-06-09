import re
from pydantic import BaseModel, ConfigDict, field_validator
from typing import Optional
from datetime import datetime

EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

def normalize_email(value: str) -> str:
    value = value.strip().lower()
    if not EMAIL_PATTERN.match(value):
        raise ValueError("Invalid email format")
    return value

def require_phone(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("Phone is required")
    return value

class EmailValidatedModel(BaseModel):
    @field_validator("email", check_fields=False)
    @classmethod
    def validate_email(cls, value: str) -> str:
        return normalize_email(value)

class PhoneRequiredModel(BaseModel):
    @field_validator("phone", check_fields=False)
    @classmethod
    def validate_phone(cls, value: str) -> str:
        return require_phone(value)

class UserInput(EmailValidatedModel, PhoneRequiredModel):
    name: str
    email: str
    role: Optional[str] = "USER"
    phone: str

class WorkspaceOut(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class UserOut(BaseModel):
    id: int
    name: str
    email: str
    phone: str
    role: str
    workspace_id: int
    email_verified: bool
    created_at: datetime
    updated_at: datetime
    workspace: WorkspaceOut

    model_config = ConfigDict(from_attributes=True) 


class User(UserOut):
    password: str
    

class InviteUser(EmailValidatedModel):
    email: str
    
class InviteUserOut(BaseModel):
    email: str
    invite_link: str





