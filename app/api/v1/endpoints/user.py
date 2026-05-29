from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.schemas.user_schema import UserInput,InviteUser
from app.schemas.response_schema import APIResponse
from app.services.user_service import add_user_service, invite_user_service
from app.api.deps import get_current_user


router=APIRouter(prefix="/user", tags=["User"])

@router.post("/create", status_code=201, response_model=APIResponse)
def add_user(data:UserInput, db:Session=Depends(get_db), current_user:dict=Depends(get_current_user)):
    return add_user_service(data, db)

@router.post("/invite")
def invite_user(data:InviteUser, db:Session=Depends(get_db), current_user:dict=Depends(get_current_user)):
    return invite_user_service(data, db)




