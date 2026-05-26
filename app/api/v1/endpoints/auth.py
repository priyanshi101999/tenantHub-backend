from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.schemas.user_schema import Register, Email, OTPInput, LoginInput
from app.services.auth_Service import verify_email_service, verify_otp_service, register_user_service,login_Service

router=APIRouter()

@router.post('/register')
def register(registerData: Register, db : Session = Depends(get_db)):
    return register_user_service(registerData, db)

@router.post("/verify-email")
def verify_email(data: Email, db:Session =Depends(get_db)):
    return verify_email_service(data.email, db)

@router.post("/verify-otp")
def verify_otp(otpData:OTPInput, db:Session=Depends(get_db)):
    return verify_otp_service(otpData, db)

@router.post("/login")
def login(loginData:LoginInput, db:Session=Depends(get_db)):
    return login_Service(loginData, db)