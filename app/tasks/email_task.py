from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from app.core.config import settings
from app.core.celery import celery_app

def send_email(email: str, subject: str, html_content: str):
    message = Mail(
        from_email=settings.sender_mail,
        to_emails=email,
        subject=subject,
        html_content=html_content
    )
    sg = SendGridAPIClient(settings.sendgrid_api_key)
    return sg.send(message)

@celery_app.task(bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=60,
    retry_jitter=True,
    max_retries=3)
def send_email_task(self, email:str, subject:str, html_content:str):
    try:
        return send_email(email, subject, html_content)
    except Exception as e:
        print("error", e)
        raise self.retry(exc=e, countdown=10)

