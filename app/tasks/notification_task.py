from app.core.celery import celery
from firebase_admin import messaging

@celery.task(bind=True,
             autoretry_for=("exception",),
             retry_backoff=True,
             retry_backoff_max=60,
             retry_jitter=True,
             max_retries=3)
def send_notification_task(self, token:str, title:str, body:str,data:dict=None):
    message=messaging,message(
        messaging.notification(
            title=title,
            body=body
        ),
        data=data or {}
        ,
        token=token
    )

    return messaging.send(message)
