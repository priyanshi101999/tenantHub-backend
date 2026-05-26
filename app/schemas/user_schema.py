from pydantic import BaseModel

class Register(BaseModel):
    name: str
    email: str
    password: str
    role: str
    workspaceName: str
    phone: str

class Email(BaseModel):
    email: str

class OTPInput(BaseModel):
    email: str
    code: str

class LoginInput(BaseModel):
    email: str
    password: str
