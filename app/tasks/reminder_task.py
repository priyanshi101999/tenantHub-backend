from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from app.core.celery import celery_app
import asyncio

from app.db.session import AsyncSessionLocal
from app.models.task import Task
from app.tasks.notification_task import send_notification_task

@celery_app.task(bind=True, 
             autoretry_for=("exception",), 
             retry_backoff=True, 
             retry_backoff_max=60, 
             retry_jitter=True, 
             max_retries=3)
def send_due_task_reminders(self):
    return asyncio.run(send_reminder())

async def send_reminder():
    async with AsyncSessionLocal() as db:
        print("Cron job is working")
        today= datetime.now(timezone.utc).date() 
        target_date=today + timedelta(days=2)

        result=await db.execute(select(Task).where(Task.due_date==target_date, Task.status!="DONE"))
        tasks=result.scalars().all()

        if not tasks:
            return

        for task in tasks:
            await send_notification_task(task.id, "Task Reminder", "Your task is due in 2 days", task.model_dump())
    



