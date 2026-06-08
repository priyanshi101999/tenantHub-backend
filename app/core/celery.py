from celery import Celery
from app.core.config import settings
from celery.schedules import crontab

celery_app=Celery(
    "worker",
    broker=settings.redis_url,
    backend=settings.redis_url
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True
)

celery_app.autodiscover_tasks(["app.tasks"])

celery_app.conf.beat_schedule={
    "send-reminder": {
        "task":"app.tasks.reminder_task.send_due_task_reminders",
        "schedule": crontab(hour=9, minute=0)
    }
}

import app.tasks.email_task
import app.tasks.stripe_task
import app.tasks.notification_task
import app.tasks.reminder_task