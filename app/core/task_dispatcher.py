import asyncio
import threading

from app.core.config import settings


def run_in_thread(func, *args, **kwargs):
    def runner():
        try:
            result = func(*args, **kwargs)
            if asyncio.iscoroutine(result):
                asyncio.run(result)
        except Exception as exc:
            print("Background task failed:", exc)

    thread = threading.Thread(target=runner, daemon=True)
    thread.start()
    return thread


def dispatch_email(email: str, subject: str, html_content: str):
    from app.tasks.email_task import send_email, send_email_task

    if settings.use_celery:
        return send_email_task.delay(email, subject, html_content)

    return run_in_thread(send_email, email, subject, html_content)


def dispatch_notification(token: str, title: str, body: str, data: dict = None):
    from app.tasks.notification_task import send_notification, send_notification_task

    if settings.use_celery:
        return send_notification_task.delay(token, title, body, data)

    return run_in_thread(send_notification, token, title, body, data)


def dispatch_stripe_event(event: dict):
    from app.tasks.stripe_task import handle_event, process_Stripe_event

    if settings.use_celery:
        return process_Stripe_event.delay(event)

    return run_in_thread(handle_event, event)
