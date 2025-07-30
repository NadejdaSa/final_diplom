from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.conf import settings


@shared_task
def send_email(subject, message, from_email, to_email):
    msg = EmailMultiAlternatives(subject, message, from_email, [to_email])
    try:
        msg.send()
        return f'Email sent to {to_email}'
    except Exception as e:
        return f'Failed to send email:{str(e)}'
