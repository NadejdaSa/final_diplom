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


@shared_task
def do_import(url, user_id):
    from django.core.exceptions import ValidationError
    from backend.models import Shop, Category, Product, ProductInfo, \
        Parameter, ProductParameter, User
    import yaml
    import requests

    try:
        response = requests.get(url)
        response.raise_for_status()
        data = yaml.safe_load(response.content)

        user = User.objects.get(id=user_id)

        shop, _ = Shop.objects.get_or_create(name=data['shop'],
                                             user_id=user.id)
        for category in data.get('categories', []):
            category_obj, _ = Category.objects.get_or_create(
                id=category['id'],
                name=category['name'])
            category_obj.shops.add(shop)

        ProductInfo.objects.filter(shop_id=shop.id).delete()

        for item in data.get('goods', []):
            product, _ = Product.objects.get_or_create(
                name=item['name'],
                category_id=item['category'])
            product_info = ProductInfo.objects.create(
                product_id=product.id,
                external_id=item['id'],
                model=item['model'],
                price=item['price'],
                price_rrc=item['price_rrc'],
                quantity=item['quantity'],
                shop_id=shop.id
            )
            for name, value in item.get('parameters', {}).items():
                parameter, _ = Parameter.objects.get_or_create(name=name)
                ProductParameter.objects.create(
                    product_info_id=product_info.id,
                    parameter_id=parameter.id,
                    value=value)
        return {'status': True}
    except Exception as e:
        return {'status': False, 'error': f'Ошибка загрузки yaml: {str(e)}'}
