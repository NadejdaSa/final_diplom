
from backend.models import ConfirmEmailToken, User
from django.dispatch import Signal, receiver
from django.core.mail import send_mail
from django.conf import settings
from typing import Type
from django.core.mail import EmailMultiAlternatives
print('[DEBUG] Импортирован backend.signals')


new_user_registered = Signal()


# Отправка письма с подтверждением почты
@receiver(new_user_registered)
def send_confirmation_email(sender, user, request, **kwargs):
    print('[DEBUG] Вызван обработчик send_confirmation_email') 
    print(f'[DEBUG] send_confirmation_email вызван для user {user.email}')

    if not user.is_active:
        token, _ = ConfirmEmailToken.objects.get_or_create(user_id=user.pk)
        subject = f'Подтверждение регистрации для {user.email}'
        message = f'Ваш токен подтверждения: {token.key}'
        from_email = settings.DEFAULT_FROM_EMAIL
        recipient_list = [user.email]
        msg = EmailMultiAlternatives(subject, message, from_email, recipient_list)
        try:
            msg.send()
        except Exception as e:
            print(f'[Ошибка отправки письма подтверждения] {e}')
