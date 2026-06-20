from datetime import datetime, timezone
from app.models.task import Task
from app.models.enums import TaskStatus
from fastapi import status, HTTPException
from fastapi.responses import FileResponse
from app.models.task_attachment import TaskAttachment
from app.models.user_device import UserDevice
from app.schemas.task_schema import AttachmentOut, TaskOut
from app.schemas.response_schema import APIResponse
from app.core.plan_features import PLAN_FEATURES
from sqlalchemy import case, func, select, update
from sqlalchemy.orm import selectinload
from app.models.user import User
from app.models.plan import Plan
import os,shutil
import math

from app.core.task_dispatcher import dispatch_email, dispatch_notification

async def get_workspace_plan(db, current_user):
        result=await db.execute(select(Plan).where(Plan.id==current_user.workspace.plan_id))

        current_plan=result.scalars().first()

        if current_plan is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
        
        return current_plan

async def mark_overdue_tasks_service(db):
    result=await db.execute(
        update(Task)
        .where(
            Task.due_date < datetime.now(timezone.utc),
            Task.status != TaskStatus.DONE,
            Task.status != TaskStatus.OVERDUE,
            Task.is_deleted == False
        )
        .values(status=TaskStatus.OVERDUE)
    )
    await db.commit()
    return getattr(result, "rowcount", 0) or 0

def apply_overdue_status(task):
    due_date = task.due_date
    if due_date is not None and due_date.tzinfo is None:
        due_date = due_date.replace(tzinfo=timezone.utc)

    if due_date is not None and due_date < datetime.now(timezone.utc) and task.status != TaskStatus.DONE:
        task.status = TaskStatus.OVERDUE

def get_plan_features(current_plan):
        return PLAN_FEATURES.get(current_plan.name.upper(), {})

async def require_plan_feature(feature_name, db, current_user):
        current_plan=await get_workspace_plan(db, current_user)
        features=get_plan_features(current_plan)

        if not features.get(feature_name, False):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"{feature_name.replace('_', ' ').title()} is not available on your current plan")
        
        return current_plan

async def check_plan(current_plan_id, db, current_user):
        result=await db.execute(select(Plan).where(Plan.id==current_plan_id))

        current_plan=result.scalars().first()

        if current_plan is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")

        result=await db.execute(select(func.count(Task.id)).where(Task.workspace_id==current_user.workspace_id, Task.is_deleted==False))
 
        task_count= result.scalar()

        if task_count >= current_plan.max_tasks:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You have reached the maximum number of tasks for this plan")
        
        return True

async def send_task_push_notifications(db, current_user, user_id, title, body, data=None):
        current_plan=await get_workspace_plan(db, current_user)
        if not get_plan_features(current_plan).get("push_notifications", False):
            return

        user_device_query=await db.execute(
            select(UserDevice).where(
                UserDevice.user_id==user_id,
                UserDevice.is_active==True
            )
        )
        user_devices=user_device_query.scalars().all()

        for device in user_devices:
            if device.fcm_token is not None:
                dispatch_notification(device.fcm_token, title, body, data)

async def send_task_email_notification(db, current_user, user_id, subject, body):
        current_plan=await get_workspace_plan(db, current_user)
        if not get_plan_features(current_plan).get("email_notifications", False):
            return

        result=await db.execute(select(User).where(User.id==user_id, User.workspace_id==current_user.workspace_id))
        user=result.scalars().first()

        if user is not None and user.email:
            dispatch_email(user.email, subject, f"<p>{body}</p>")
        
async def create_task_service(data, db, current_user):
    allowed=await check_plan(current_user.workspace.plan_id, db, current_user)

    if not allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You have reached the maximum number of tasks for this plan")
    
    

    task_data=data.model_dump()
    task_data["created_by"] =current_user.id
    task_data["workspace_id"]=current_user.workspace_id
    assignee=None

    if task_data["assignee_id"] is not None:
        result=await db.execute(select(User).where(User.id==task_data["assignee_id"], User.workspace_id==current_user.workspace_id))
        assignee=result.scalars().first()

        if assignee==None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignee not found in your workspace")

    try:
        task = Task(**task_data)
        apply_overdue_status(task)
        db.add(task)
        await db.commit()
        task_id = task.id

        result = await db.execute(
            select(Task)
            .options(selectinload(Task.attachments.and_(TaskAttachment.is_deleted == False)))
            .where(
                Task.id == task_id,
                Task.workspace_id == current_user.workspace_id,
                Task.is_deleted == False
            )
        )
        task = result.scalars().first()

        if assignee is not None:
            await send_task_push_notifications(
                db,
                current_user,
                assignee.id,
                "New Task Assigned",
                f"You have been assigned: {task.title}",
                {"task_id": str(task.id)}
            )
            await send_task_email_notification(
                db,
                current_user,
                assignee.id,
                "New Task Assigned",
                f"You have been assigned: {task.title}"
            )

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
        result=await db.execute(select(Task).options(selectinload(Task.attachments.and_(TaskAttachment.is_deleted == False))).where(Task.id==task_id))
        existing_task=result.scalars().first()

        if existing_task==None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
        
        if existing_task.workspace_id != current_user.workspace_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can not update task from other workspace")
        
        if update_data.get("assignee_id") is not None:
            result=await db.execute(select(User).where(User.id==update_data["assignee_id"], User.workspace_id==current_user.workspace_id))
            assignee=result.scalars().first()

            if assignee==None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignee not found in your workspace")

            await send_task_push_notifications(
                db,
                current_user,
                assignee.id,
                "New Task Assigned",
                f"You have been assigned: {existing_task.title}",
                {"task_id": str(existing_task.id)}
            )
            await send_task_email_notification(
                db,
                current_user,
                assignee.id,
                "New Task Assigned",
                f"You have been assigned: {existing_task.title}"
            )
        
        for field, value in update_data.items():
            setattr(existing_task, field, value)

        apply_overdue_status(existing_task)

        if update_data.get("status") is not None:
            if existing_task.status == TaskStatus.DONE:
                await send_task_push_notifications(db, current_user, existing_task.created_by, "Task Completed", "Your task has been completed")
                await send_task_email_notification(db, current_user, existing_task.created_by, "Task Completed", "Your task has been completed")
            if existing_task.status == TaskStatus.IN_PROGRESS:
                await send_task_push_notifications(db, current_user, existing_task.created_by, "Task In Progress", "Your task is in progress")
                await send_task_email_notification(db, current_user, existing_task.created_by, "Task In Progress", "Your task is in progress")

        
        db.add(existing_task)
        await db.commit()

        result = await db.execute(
            select(Task)
            .options(selectinload(Task.attachments.and_(TaskAttachment.is_deleted == False)))
            .where(
                Task.id == task_id,
                Task.workspace_id == current_user.workspace_id,
                Task.is_deleted == False
            )
        )
        existing_task = result.scalars().first()

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
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update task")


async def delete_task_service(id, db, current_user):
    try:
        result = await db.execute(select(Task).options(selectinload(Task.attachments)).where(Task.id == id, Task.workspace_id == current_user.workspace_id, Task.is_deleted == False))
        task = result.scalars().first()

        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

        task.is_deleted = True
        for attachment in task.attachments:
            attachment.is_deleted = True
            if attachment.file_path and os.path.exists(attachment.file_path):
                os.remove(attachment.file_path)
            db.add(attachment)

        db.add(task)
        await db.commit()

        return APIResponse(
            message="Task removed successfully",
            status=status.HTTP_200_OK
        )

    except HTTPException:
        await db.rollback()
        raise

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to remove task")

async def get_task_list__service( db, current_user, page, size, task_status, priority, overdue, assignee_id):
    
    try:
        if page < 1 or size < 1 or size > 100:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid pagination parameters")
        
        query=select(Task).options(selectinload(Task.attachments.and_(TaskAttachment.is_deleted == False))).where(Task.workspace_id==current_user.workspace_id, Task.is_deleted==False)

        if task_status:
            query=query.where(Task.status==task_status)

        if priority:
            query=query.where(Task.priority==priority)

        if assignee_id:
            query=query.where(Task.assignee_id==assignee_id)

        if overdue:
            query=query.where(Task.due_date < datetime.now(timezone.utc), Task.status != TaskStatus.DONE)

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
            count_result=count_result.where(Task.due_date < datetime.now(timezone.utc), Task.status != TaskStatus.DONE)
        
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

        await require_plan_feature("file_attachments", db, current_user)
        
        upload_dir = f"uploads/{current_user.workspace_id}/{task_id}/"
        os.makedirs(upload_dir, exist_ok=True)

        file_name = os.path.basename(file.filename)
        file_path= os.path.join(upload_dir, file_name)
        with open(file_path,"wb") as f:
            shutil.copyfileobj(file.file, f)

        attachment= TaskAttachment(
            task_id=task_id,
            file_name=file_name,
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
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to attach file")

async def open_attachment_service(attachment_id, db, current_user):
    try:
        result = await db.execute(
            select(TaskAttachment)
            .join(Task, Task.id == TaskAttachment.task_id)
            .where(
                TaskAttachment.id == attachment_id,
                TaskAttachment.is_deleted == False,
                Task.workspace_id == current_user.workspace_id,
                Task.is_deleted == False
            )
        )
        attachment = result.scalars().first()

        if attachment is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")

        if not os.path.exists(attachment.file_path):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

        return FileResponse(
            attachment.file_path,
            media_type=attachment.content_type,
            filename=attachment.file_name
        )

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to open attachment")

async def delete_attachment_service(attachment_id, db, current_user):
    try:
        result = await db.execute(
            select(TaskAttachment)
            .join(Task, Task.id == TaskAttachment.task_id)
            .where(
                TaskAttachment.id == attachment_id,
                TaskAttachment.is_deleted == False,
                Task.workspace_id == current_user.workspace_id,
                Task.is_deleted == False
            )
        )
        attachment = result.scalars().first()

        if attachment is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")

        if attachment.file_path and os.path.exists(attachment.file_path):
            os.remove(attachment.file_path)

        attachment.is_deleted = True
        db.add(attachment)
        await db.commit()

        return APIResponse(
            message="File deleted successfully",
            status=status.HTTP_200_OK
        )

    except HTTPException:
        await db.rollback()
        raise

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete attachment")

async def get_analytics_service(db, current_user):
    try:
        now = datetime.now(timezone.utc)
        query=select(
            func.count().label("total"),
            func.sum(case((Task.status==TaskStatus.TODO,1),else_=0)).label("todo"),
            func.sum(case((Task.status==TaskStatus.IN_PROGRESS,1),else_=0)).label("in_progress"),
            func.sum(case((Task.status==TaskStatus.DONE, 1), else_=0)).label("done"),
            func.sum(case(((Task.due_date < now) & (Task.status != TaskStatus.DONE), 1), else_=0)).label("overdue")
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
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve analytics")
    
async def get_task_service(id, db, current_user):
    try:
        result=await db.execute(select(Task).options(selectinload(Task.attachments.and_(TaskAttachment.is_deleted == False))).where(Task.id==id, Task.workspace_id==current_user.workspace_id, Task.is_deleted==False))
        task=result.scalars().first()

        if task==None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
        
        return APIResponse(
            message="Task retrieved successfully",
            status=status.HTTP_200_OK,
            data=TaskOut.model_validate(task)
        )
    
    except HTTPException:
        await db.rollback()
        raise

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve task")

    
