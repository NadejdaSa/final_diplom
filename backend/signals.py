
from backend.models import ConfirmEmailToken
from django.dispatch import Signal, receiver
from django.conf import settings
from backend.tasks import send_email
from django_rest_passwordreset.signals import reset_password_token_created
from django.template.loader import render_to_string

new_user_registered = Signal()
email_confirmed = Signal()
new_order_status = Signal()


def generate_invoice_text(order, shop):
    items = order.items.filter(shop=shop).select_related(
        'product__product', 'shop')

    # Вычисление итоговой суммы заказа
    total_sum = sum(item.quantity * item.product.price for item in items)

    return render_to_string(
        'invoice.txt',
        {
            'order': order,
            'items': items,
            'shop': shop,
            'total_sum': total_sum
        }
    )


# Отправка письма с подтверждением почты
@receiver(new_user_registered)
def send_confirmation_email(sender, user, request, **kwargs):
    if not user.is_active:
        token, _ = ConfirmEmailToken.objects.get_or_create(user_id=user.pk)
        subject = f'Подтверждение регистрации для {user.email}'
        message = f'Ваш токен подтверждения: {token.key}'
        from_email = settings.DEFAULT_FROM_EMAIL
        send_email.delay(subject, message, from_email, user.email)


# Отправка письма об успешной регистрации
@receiver(email_confirmed)
def send_registration_email(sender, user, **kwargs):
    subject = 'Регистрация прошла успешно'
    message = f'Здравствуйте, {user.username}! Ваш email успешно подтвержден!'
    from_email = settings.DEFAULT_FROM_EMAIL
    send_email.delay(subject, message, from_email, user.email)


# Отправка письма об успешном заказе
@receiver(new_order_status)
def send_order_email(sender, order, **kwargs):
    status_messages = {
        'new': 'Ваш заказ успешно оформлен!',
        'confirmed': 'Ваш заказ подтвержден магазином!',
        'assembled': 'Ваш заказ собран и готов к отправке.',
        'sent': 'Ваш заказ отправлен.',
        'delivered': 'Ваш заказ доставлен.',
        'cancelled': 'Ваш заказ был отменен.',
    }

    subject = f'Обновление статуса заказа #{order.id}'
    message = f'Здравствуйте, {order.user.username}!\n\n' \
              f'{status_messages.get(order.status, "Статус заказа обновлен.")}'

    from_email = settings.DEFAULT_FROM_EMAIL
    send_email.delay(subject, message, from_email, order.user.email)

    if order.status == 'new':
        shops = set(item.shop for item in order.items.all())
        for shop in shops:
            if shop.user and shop.user.email:
                subject_shop = f'Новая накладная по заказу #{order.id}'
                invoice_text = generate_invoice_text(order, shop)
                send_email.delay(
                    subject_shop,
                    invoice_text,
                    settings.DEFAULT_FROM_EMAIL,
                    shop.user.email
                )


# Сброс пароля
@receiver(reset_password_token_created)
def password_reset_token_created(sender, reset_password_token, **kwargs):
    user = reset_password_token.user
    subject = 'Сброс пароля'
    message = f'Здравствуйте, {user.username}!\n' \
        f'Ваш токен для сброса пароля: \n' \
        f'{reset_password_token.key}'
    from_email = settings.DEFAULT_FROM_EMAIL
    to_email = user.email
    send_email.delay(subject, message, from_email, to_email)
