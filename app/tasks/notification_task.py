from app.core.celery import celery_app
import app.core.firebase_config
from firebase_admin import messaging

def send_notification(token: str, title: str, body: str, data: dict = None):
    message=messaging.Message(
        notification=messaging.Notification(
            title=title,
            body=body
        ),
        data={str(key): str(value) for key, value in (data or {}).items()},
        token=token
    )

    return messaging.send(message)

@celery_app.task(bind=True,
             autoretry_for=(Exception,),
             retry_backoff=True,
             retry_backoff_max=60,
             retry_jitter=True,
             max_retries=3)
def send_notification_task(self, token:str, title:str, body:str,data:dict=None):
    return send_notification(token, title, body, data)
