from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.schemas.auth_schema import Register, EmailInput, OTPInput, LoginInput,RefreshToken,ResetPassword
from app.models.user import User
from app.services.auth_Service import verify_email_service, verify_otp_service, register_user_service,login_Service,refresh_token_Service,change_password_service,forget_password_service,reset_password_service
from app.api.deps import get_current_user
from app.schemas.auth_schema import ChangePassword

router=APIRouter(prefix="/auth", tags=["Authentication"])

@router.post('/register')
def register(registerData: Register, db : Session = Depends(get_db)):
    return register_user_service(registerData, db)

@router.post("/verify-email")
def verify_email(data: EmailInput, db:Session =Depends(get_db)):
    return verify_email_service(data.email, db)

@router.post("/verify-otp")
def verify_otp(otpData:OTPInput, db:Session=Depends(get_db)):
    return verify_otp_service(otpData, db)

@router.post("/login")
def login(loginData:LoginInput, db:Session=Depends(get_db)):
    return login_Service(loginData, db)

@router.post("/refresh-token")
def refresh_token(data:RefreshToken, db:Session=Depends(get_db)):
    return refresh_token_Service(data, db)

@router.post("/change-password")
def change_password(data:ChangePassword, db:Session=Depends(get_db), currect_user: User=Depends(get_current_user)):
    return change_password_service(data, db, currect_user)

@router.post("/forgot-password")
def forgot_password(data:EmailInput):
    return forget_password_service(data)

@router.post("/reset-password")
def reset_password(data:ResetPassword, db:Session=Depends(get_db)):
    return reset_password_service(data, db)
