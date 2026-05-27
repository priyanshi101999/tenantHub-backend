from pydantic import BaseModel

class Register(BaseModel):
    name: str
    email: str
    password: str
    role: str
    workspaceName: str
    phone: str

class EmailInput(BaseModel):
    email: str

class OTPInput(BaseModel):
    email: str
    code: str

class ResetPassword(OTPInput):
    new_password: str

class LoginInput(BaseModel):
    email: str
    password: str

class RefreshToken(BaseModel):
    refresh_token: str

class ChangePassword(BaseModel):
    old_password: str
    new_password: str