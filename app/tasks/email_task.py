from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from app.core.config import settings
from app.core.celery import celery

@celery.Task(bind=True, max_retries=3)
def send_email_task(self, email:str, subject:str, html_content:str):
    print("send_email", email, subject, html_content, settings.sender_mail, settings.sendgrid_api_key)
    try:
        message = Mail(
            from_email=settings.sender_mail,
            to_emails=email,
            subject=subject,
            html_content=html_content
        )
        print("message", settings.sendgrid_api_key)
        sg=SendGridAPIClient(settings.sendgrid_api_key)
        print("sg.send",sg)
        response=sg.send(message)
        print("response.status_code",response)
        return response
    except Exception as e:
        print("error", e)
        raise self.retry(exc=e, countdown=10)

