
from backend.models import ConfirmEmailToken
from django.dispatch import Signal, receiver
from django.core.mail import send_mail
from django.conf import settings

new_user_registered = Signal()


# Отправка письма с подтверждением почты
@receiver(new_user_registered)
def send_confirmation_email(sender, user, **kwargs):
    token, _ = ConfirmEmailToken.objects.get_or_create(user=user)
    confirm_url = f'http://localhost:8000/api/v1/user/confirm/?token={token.key}&email={user.email}'
    send_mail(
        'Подтверждение регистрации',
        f'Перейдите по ссылке для подтверждения: {confirm_url}',
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )
