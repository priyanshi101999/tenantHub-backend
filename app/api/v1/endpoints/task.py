from fastapi import APIRouter, Depends, Query
from app.api.deps import get_db,get_current_user
from app.schemas.response_schema import APIResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.task_service import create_task_service, update_task_service, get_tasks_service
from app.schemas.user_schema import User
from app.schemas.task_schema import TaskInput, TaskUpdate


router=APIRouter(prefix="/task", tags=["Task"])

@router.post("/create", status_code=201, response_model=APIResponse)
async def create_task(data: TaskInput, db:AsyncSession=Depends(get_db), current_user:User=Depends(get_current_user)):
    return await create_task_service(data, db, current_user)

@router.patch("/update", status_code=200, response_model=APIResponse)
async def update_task(data: TaskUpdate,id:int=Query(...),  db:AsyncSession=Depends(get_db), current_user:User=Depends(get_current_user)):
    return await update_task_service(id,data, db, current_user)

@router.get("/list", status_code=200, response_model=APIResponse)
async def get_tasks(db:AsyncSession=Depends(get_db), current_user:User=Depends(get_current_user)):
    return await get_tasks_service(db, current_user)

