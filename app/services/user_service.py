from app.models.user import User
from fastapi import HTTPException, status
from app.schemas.response_schema import APIResponse
from app.schemas.user_schema import UserOut, InviteUserOut
from app.core.redis_client import redis_client as redis
from app.utils.secret_key import generate_invite_token
from app.core.config import settings
from app.tasks.email_task import send_email_task
from app.templates.invite_mail import get_invite_email_template

def add_user_service(data, db):
    data = data.model_dump()

    try:
        existing_user = db.query(User).filter(User.email == data["email"]).first()

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User already exists"
            )

        user = User(**data)
        db.add(user)
        db.commit()
        db.refresh(user)

        return APIResponse(
            status="success",
            message="User added successfully",
            data={"user": UserOut.model_validate(user)}
        )

    except HTTPException:
        db.rollback()
        raise

    except Exception as e:
        db.rollback()
        print("Error:", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add user"
        )
    
    
def invite_user_service(data, db):
    email=data.email

    existing_user=db.query(User).filter(User.email==email).first()

    if existing_user==None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    

    secret_token=generate_invite_token()

    redis.set(f"invite_token:{secret_token}", email, ex=86400)

    invite_link=f"{settings.frontend_baseurl}/invite/{secret_token}"


    html_template=get_invite_email_template(invite_link, "24 hours")

    send_email_task.delay(email, "Invite User", html_template)

    output_data={
        "email": email,
        "invite_link": invite_link
    }

    return APIResponse(
        message="Invite sent successfully",
        data=InviteUserOut.model_validate(output_data),
        status=status.HTTP_200_OK
    )



 
 