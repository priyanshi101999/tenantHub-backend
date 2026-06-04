from datetime import datetime

from app.models.task import Task
from fastapi import status, HTTPException
from app.models.task_attachment import TaskAttachment
from app.models.user_device import UserDevice
from app.schemas.task_schema import AttachmentOut, TaskOut
from app.schemas.response_schema import APIResponse
from app.core.plan_features import PLAN_FEATURES
from sqlalchemy import case, func, select
from app.models.user import User
from app.models.plan import Plan
from sqlalchemy.orm import selectinload
import os,shutil
import math

from app.tasks.notification_task import send_notification_task

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

    if task_data["assignee_id"] is not None:
        result=await db.execute(select(User).where(User.id==task_data["assignee_id"], User.workspace_id==current_user.workspace_id))
        assignee=result.scalars().first()

        if assignee==None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignee not found in your workspace")
        
        user_device_query=await db.execute(select(UserDevice).where(UserDevice.user_id==assignee.id))
        user_device=user_device_query.scalars().all()

        for device in user_device:
            if device.fcm_token is not None:
                send_notification_task.delay(device.fcm_token, "New Task Assigned", "You have been assigned a new task", task_data)

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
        
        if update_data["assignee_id"] is not None:
            result=await db.execute(select(User).where(User.id==update_data["assignee_id"], User.workspace_id==current_user.workspace_id))
            assignee=result.scalars().first()

            user_device_query=await db.execute(select(UserDevice).where(UserDevice.user_id==assignee.id))
            user_device=user_device_query.scalars().all()

            for device in user_device:
                if device.fcm_token is not None:
                    send_notification_task.delay(device.fcm_token, "New Task Assigned", "You have been assigned a new task")

            if assignee==None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignee not found in your workspace")
        
        for field, value in update_data.items():
            setattr(existing_task, field, value)

        if update_data["status"] is not None:
            user_device_query=await db.execute(select(UserDevice).where(UserDevice.user_id==existing_task.created_by))
            user_device=user_device_query.scalars().all()

            for device in user_device:
                if device.fcm_token is not None:
                    if update_data["status"] == "DONE":
                        send_notification_task.delay(device.fcm_token, "Task Completed", "Your task has been completed")
                    if update_data["status"] == "IN_PROGRESS":
                        send_notification_task.delay(device.fcm_token, "Task In Progress", "Your task is in progress")

        
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

async def get_tasks_service( db, current_user, page, size, task_status, priority, overdue, assignee_id):
    try:
        if page < 1 or size < 1 or size > 100:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid pagination parameters")
        
        query=select(Task).where(Task.workspace_id==current_user.workspace_id, Task.is_deleted==False)

        if task_status:
            query=query.where(Task.status==task_status)

        if priority:
            query=query.where(Task.priority==priority)

        if assignee_id:
            query=query.where(Task.assignee_id==assignee_id)

        if overdue:
            query=query.where(Task.due_date < datetime.utcnow(), Task.status != "DONE")

        result=await db.execute(query.order_by(Task.created_at.desc()).limit(size).offset((page-1)*size))
        tasks=result.scalars().all()
    

        count_result=select(func.count(Task.id)).where(Task.workspace_id==current_user.workspace_id, Task.is_deleted==False)
        if task_status:
            count_result=count_result.where(Task.status==task_status)

        if priority:
            count_result=count_result.where(Task.priority==priority)
        
        if assignee_id:
            count_result=count_result.where(Task.assignee_id==assignee_id)

        if overdue:
            count_result=count_result.where(Task.due_date < datetime.utcnow(), Task.status != "DONE")
        
        total_items=(await db.execute(count_result)).scalar()

        data=[TaskOut.model_validate(task) for task in tasks]
        return APIResponse(
            message="Tasks retrieved successfully",
            status=status.HTTP_200_OK,
            data={
                "tasks":data,
                "pagination":{
                    "page": page,
                    "size": size,
                    "total_pages": math.ceil(total_items/size),
                    "total_items": total_items
                }
            }
        )
    
    except HTTPException:
        db.rollback()
        raise
    
    except Exception as e:
        print("error", e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to retrieve tasks")
    
async def attach_file_Service(task_id,file, db, current_user):
    try:
        result = await db.execute(select(Task).where(Task.id == task_id, Task.workspace_id == current_user.workspace_id))
        task = result.scalars().first()

        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
        
        allowed=["image/jpeg", "image/png", "application/pdf"]

        if file.content_type not in allowed:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File type not allowed")
        
        upload_dir = f"uploads/{current_user.workspace_id}/{task_id}/"
        os.makedirs(upload_dir, exist_ok=True)

        file_path= f"{upload_dir}/{file.filename}"
        with open(file_path,"wb") as f:
            shutil.copyfileobj(file.file, f)

        attachment= TaskAttachment(
            task_id=task_id,
            file_name=file.filename,
            file_size=os.path.getsize(file_path),
            content_type=file.content_type,
            file_path=file_path,
            uploaded_by=current_user.id
        )

        db.add(attachment)
        await db.commit()
        return APIResponse(
            message="File attached successfully",
            status=status.HTTP_200_OK,
            data=AttachmentOut.model_validate(attachment)
        )
    except HTTPException:
        await db.rollback()
        raise

    except Exception as e:
        await db.rollback()
        print("error", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to attach file")
    

async def get_analytics_service(db, current_user):
    try:
        query=select(
            func.count().label("total"),
            func.sum(case((Task.status=="TODO",1),else_=0)).label("todo"),
            func.sum(case((Task.status=="IN_PROGRESS",1),else_=0)).label("in_progress"),
            func.sum(case((Task.status=="DONE", 1), else_=0)).label("done"),
            func.sum(case((Task.due_date <datetime.utcnow(),1), else_=0)).label("overdue")
        ).where(Task.workspace_id==current_user.workspace_id, Task.is_deleted==False)
        
        result=await db.execute(query)
        analytics=result.first()

        return APIResponse(
            message="Analytics retrieved successfully",
            status=status.HTTP_200_OK,
            data={
                "total_tasks": analytics.total or 0,
                "todo": analytics.todo or 0,
                "in_progress": analytics.in_progress or 0,
                "done": analytics.done or 0,
                "overdue": analytics.overdue or 0
            }
        )
    
    except Exception as e:
        await db.rollback()
        print("error", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve analytics")