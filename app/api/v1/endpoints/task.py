from fastapi import APIRouter, Depends
from app.api.deps import get_db,get_current_user, check_plan
from app.schemas.response_schema import APIResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.task_service import create_task_service
from app.models.user import User
from app.schemas.task_schema import TaskInput


router=APIRouter(prefix="/task", tags=["Task"])

@router.post("/create", status_codd=201, response_model=APIResponse)
async def create_task(data: TaskInput, db:AsyncSession=Depends(get_db), current_user:User=Depends(check_plan(action="create_task"))):
    return await create_task_service(data, db, current_user)