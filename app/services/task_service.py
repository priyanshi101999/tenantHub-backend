from app.models.task import Task
from fastapi import status, HTTPException
from app.schemas.task_schema import TaskOut
from app.schemas.response_schema import APIResponse
from app.core.plan_features import PLAN_FEATURES
from sqlalchemy import func, select
from app.models.plan import Plan
from sqlalchemy.orm import selectinload

async def check_plan(current_plan_id, db, current_user):
        result=await db.execute(select(Plan).where(Plan.id==current_plan_id))

        current_plan=result.scalars().first()

        if current_plan is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")

        result=await db.execute(select(func.count(Task.id)).where(Task.workspace_id==current_user.workspace_id))
 
        task_count= result.scalar()

        print("Task count:", task_count)
        print("Current plan:", PLAN_FEATURES['PRO']["max_tasks"])

        if task_count > PLAN_FEATURES[current_plan.name]["max_tasks"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You have reached the maximum number of tasks for this plan")
        
        return True
        


async def create_task_service(data, db, current_user):
    allowed=await check_plan(current_user.workspace.plan_id, db, current_user)

    if not allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You have reached the maximum number of tasks for this plan")

    task_data=data.model_dump()
    task_data["created_by"] =current_user.id
    task_data["workspace_id"]=current_user.workspace_id
    
    try:
        task = Task(**task_data)
        db.add(task)
        await db.commit()
        await db.refresh(task)

        print("Task created with ID:", task.title)

        return APIResponse(
            status=status.HTTP_201_CREATED,
            data=TaskOut.model_validate(task),
            message="Task created successfully"
        )

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create task")

async def update_task_service(id,data, db, current_user):
    
    task_id=id
    update_data=data.model_dump(exclude_unset=True)

    try:
        result=await db.execute(select(Task).where(Task.id==task_id))
        existing_task=result.scalars().first()

        if existing_task==None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
        
        if existing_task.workspace_id != current_user.workspace_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can not update task from other workspace")
        
        for field, value in update_data.items():
            setattr(existing_task, field, value)
        
        db.add(existing_task)
        await db.commit()
        await db.refresh(existing_task)
        return APIResponse(
            message="Task updated successfully",
            status=status.HTTP_200_OK,
            data= TaskOut.model_validate(existing_task)
        )
    
    except HTTPException:
        await db.rollback()
        raise 

    except Exception as e:
        await db.rollback()
        print("error", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update task")

async def get_tasks_service(db, current_user):
    try:
        result=await db.execute(select(Task).options(selectinload(Task.assignee)).where(Task.workspace_id==current_user.workspace_id, Task.is_deleted==False))
        tasks=result.scalars().all()
        return APIResponse(
            message="Tasks retrieved successfully",
            status=status.HTTP_200_OK,
            data=[TaskOut.model_validate(task) for task in tasks]
        )
    
    except Exception as e:
        print("error", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve tasks")
    

