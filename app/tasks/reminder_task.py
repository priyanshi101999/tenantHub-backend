from datetime import datetime, timedelta, timezone
from sqlalchemy import func, select
from app.core.celery import celery_app
import asyncio

from app.db.session import AsyncSessionLocal
from app.models.enums import TaskStatus
from app.models.plan import Plan
from app.models.task import Task
from app.models.workspace import Workspace
from app.core.plan_features import PLAN_FEATURES
from app.core.task_dispatcher import dispatch_notification
from app.models.user_device import UserDevice

@celery_app.task(bind=True, 
             autoretry_for=(Exception,), 
             retry_backoff=True, 
             retry_backoff_max=60, 
             retry_jitter=True, 
             max_retries=3)
def send_due_task_reminders(self):
    return asyncio.run(send_reminder())

async def send_reminder():
    async with AsyncSessionLocal() as db:
        today= datetime.now(timezone.utc).date() 
        target_date=today + timedelta(days=2)

        result=await db.execute(
            select(Task).where(
                func.date(Task.due_date)==target_date,
                Task.status!=TaskStatus.DONE,
                Task.assignee_id.is_not(None),
                Task.is_deleted==False
            )
        )
        tasks=result.scalars().all()

        if not tasks:
            return

        for task in tasks:
            plan_query=await db.execute(
                select(Plan)
                .join(Workspace, Workspace.plan_id == Plan.id)
                .where(Workspace.id == task.workspace_id)
            )
            current_plan=plan_query.scalars().first()

            if current_plan is None or not PLAN_FEATURES.get(current_plan.name.upper(), {}).get("push_notifications", False):
                continue

            device_query=await db.execute(
                select(UserDevice).where(
                    UserDevice.user_id==task.assignee_id,
                    UserDevice.is_active==True
                )
            )
            devices=device_query.scalars().all()

            for device in devices:
                if device.fcm_token is not None:
                    dispatch_notification(
                        device.fcm_token,
                        "Task Reminder",
                        "Your task is due in 2 days",
                        {"task_id": str(task.id)}
                    )
    
