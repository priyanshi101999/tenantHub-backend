from pydantic import BaseModel

class User(BaseModel):
    name: str
    email: str
    role: str
    workspace_id: int
    phone: str
    email_verified: bool
    created_at: str
    updated_at: str
    password: str


