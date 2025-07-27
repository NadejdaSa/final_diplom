
from backend.models import ConfirmEmailToken, User
from django.dispatch import Signal, receiver
from django.core.mail import send_mail
from django.conf import settings
from typing import Type
from django.db.models.signals import post_save
from django.core.mail import EmailMultiAlternatives
from django.dispatch import Signal

new_user_registered = Signal()
email_confirmed = Signal()
new_order_status = Signal()


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


# Отправка письма об успешной регистрации
@receiver(email_confirmed)
def send_registration_email(sender, user, **kwargs):
    send_mail(
            subject='Регистрация прошла успешно',
            message=f'Здравствуйте, {user.username}! Ваш email успешно подтвержден!',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )


# Отправка письма об успешном заказе
@receiver(new_order_status)
def send_order_email(sender, order, **kwargs):
    send_mail(
            subject='Заказ успешно оформлен',
            message=f'Здравствуйте, {order.user.username}! Ваш заказ успешно оформлен!',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.user.email],
            fail_silently=False,
        )
