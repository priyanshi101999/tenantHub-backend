from app.models.workspace import Workspace
from app.models.user import User
from app.models.otp import OTP 
from app.models.refresh_token import RefreshToken
from app.core.security import hash_pasword, verify_password, create_jwt_token, create_refresh_token
from app.templates.otp_email import otp_email_template
from app.core.email import send_email
from app.utils.otp import generate_otp
from datetime import datetime, timedelta, timezone
from app.core.config import settings
from app.schemas.user_schema import OTPInput


def register_user_service(registerData, db):
    print(registerData)

    existing_email=db.query(User).filter(User.email==registerData.email).first()

    if existing_email:
        return {"message": "Email already exists"}

    workSpaceData={
        "name": registerData.workspaceName,
        "owner_id" : None
    }

    workspace=Workspace(**workSpaceData)
    db.add(workspace)
    db.flush()

    hashed_password=hash_pasword(registerData.password)
    
    userData={
        "name": registerData.name,
        "email": registerData.email,
        "password": hashed_password,
        "workspace_id": workspace.id,
        "email_verified": False
    }

    user=User(**userData)
    db.add(user)
    db.flush()

    workspace.owner_id=user.id
    db.commit()

    return {"message": "success", "data": registerData}


def verify_email_service(email, db):
    otp=generate_otp()
    print("otp", otp)
    html_content=otp_email_template(otp)

    response=send_email(email, "Email Verification", html_content)
    if response.status_code==202:

        db.query(OTP).filter(OTP.email==email).delete()

        otp_data={
            "email":email,
            "code":otp,
            "expire_at": datetime.now(timezone.utc) + timedelta(minutes=settings.otp_expire_minutes)
        }

        print("otp_Data", otp_data)

        try:
            db.add(OTP(**otp_data))
            db.commit()
        except Exception as e:
            print(e)
            db.rollback()

        return {"message": "Email sent successfully"}
    else:
        return {"message": "Email sending failed"}
    
def verify_otp_service(OtpData: OTPInput,db):

    existing_otp=db.query(OTP).filter(OTP.email==OtpData.email).first()
    print("existing_otp", {
    "email": existing_otp.email,
    "code": existing_otp.code
})

    if datetime.now(timezone.utc) > existing_otp.expire_at:
        return {"message": "OTP expired"}
    
    if existing_otp.code==OtpData.code:
        try:
            user_query=db.query(User).filter(User.email==OtpData.email)
            
            if user_query.first() == None:
                return {"message": "User not found"}
            
            user_query.update({"email_verified": True }, synchronize_session=False)

            db.query(OTP).filter(OTP.email==OtpData.email).delete()
            db.commit()
            return {"message": "Otp verified success"}
        except Exception as e:
            print(e)
            db.rollback()
    else:
        return {"message": "Invalid OTP"}


def login_Service(loginData,db):
    email=loginData.email
    password=loginData.password

    existing_user=db.query(User).filter(User.email==email).first()

    if existing_user == None:
        return {"message": "User not found"}
    
    if existing_user.email_verified == False:
        return {"message": "Email not verified, please verify your email"}
    
    if verify_password(password, existing_user.password) == False:
        return {"message": "Invalid password"}
    
    access_token=create_jwt_token({"user_id": existing_user.id, "workspace_id": existing_user.workspace_id})
    refresh_token=create_refresh_token({"user_id": existing_user.id, "workspace_id": existing_user.workspace_id})

    refresh_Token_data={
        "user_id":existing_user.id,
        "token":refresh_token,
        "expired_at":datetime.now(timezone.utc)+timedelta(days=settings.refresh_token_expire_days)
    }

    try:
        db.add(RefreshToken(**refresh_Token_data))
        db.commit()
    except Exception as e:
        print(e)
        db.rollback()

    return {"message": "Login success", "access_token": access_token, "refresh_token": refresh_token,"token_type": "Bearer"}

