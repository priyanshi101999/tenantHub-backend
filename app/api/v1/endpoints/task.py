from fastapi import APIRouter, Depends, File, Query, UploadFile
from app.api.deps import check_plan, get_db,get_current_user
from app.schemas.response_schema import APIResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.task_service import attach_file_Service, create_task_service, get_analytics_service, get_task_service, get_task_list__service, update_task_service
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
async def get_tasks_list(page:int=Query(1, gte=1),
                    size:int=Query(10, gte=1, lte=100),
                    task_status: str |None = Query(None),
                    priority: str |None = Query(None),
                    overdue: bool |None = Query(None),
                    assignee_id: int |None = Query(None),
                    db:AsyncSession=Depends(get_db), current_user:User=Depends(get_current_user)):
    return await get_task_list__service(db, current_user,page, size, task_status, priority, overdue, assignee_id)

@router.post("/attachment", status_code=201, response_model=APIResponse)
async def attach_file(task_id:int = Query(...), file : UploadFile=File(...), db:AsyncSession=Depends(get_db), current_user:User=Depends(check_plan(["PRO","ENTERPRISE"]))):
    return await attach_file_Service(task_id, file, db, current_user)

@router.get("/analytics", status_code=200, response_model=APIResponse)
async def get_analytics(db:AsyncSession=Depends(get_db), current_user:User=Depends(get_current_user)):
    return await get_analytics_service(db, current_user)


@router.get("/", status_code=200, response_model=APIResponse)
async def get_task(id:int=Query(...), db:AsyncSession=Depends(get_db), current_user:User=Depends(get_current_user)):
    return await get_task_service(id, db, current_user)