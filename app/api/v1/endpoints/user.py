from fastapi import APIRouter, Depends, Query
from app.api.deps import get_current_user, get_db, require_role
from app.models.enums import Role
from app.models.user import User
from app.schemas.user_schema import UserInput,InviteUser
from app.schemas.response_schema import APIResponse
from app.services.user_service import add_user_service, delete_user_service, get_user_service, invite_user_service,user_list_service
from sqlalchemy.ext.asyncio import AsyncSession

router=APIRouter(prefix="/user", tags=["User"])

@router.post("/create", status_code=201, response_model=APIResponse)
async def add_user(data:UserInput, db:AsyncSession=Depends(get_db), current_user:User=Depends(require_role(Role.ADMIN))):
    return await add_user_service(data, db, current_user)

@router.post("/invite", status_code=201, response_model=APIResponse)
async def invite_user(data:InviteUser, db:AsyncSession=Depends(get_db), current_user:User=Depends(require_role(Role.ADMIN))):
    return await invite_user_service(data, db)

@router.get("/list", status_code=200, response_model=APIResponse)
async def user_list(page: int = Query(1, gte=1), size: int = Query(10, gte=1, lte=100), db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    return await user_list_service(page, size, db, current_user)

@router.delete("/", status_code=200, response_model=APIResponse)
async def delete_user(id:int=Query(...),db:AsyncSession=Depends(get_db), current_user:User=Depends(require_role(Role.ADMIN))):
    return await delete_user_service(id,db, current_user)

@router.get("/", status_code=200, response_model=APIResponse)
async def get_user(id:int=Query(...),db:AsyncSession=Depends(get_db), current_user:User=Depends(get_current_user)):
    return await get_user_service(id, db, current_user)


