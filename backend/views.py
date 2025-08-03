from decimal import Decimal
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.authtoken.models import Token
import yaml
from .serializers import ContactSerializer, OrderSerializer, \
    ProductInfoSerializer, ShopSerializer
from .models import ConfirmEmailToken, Contact, Order, OrderItem, \
    ProductInfo, Shop, User
from backend.signals import new_user_registered, email_confirmed, \
    new_order_status
from django.contrib.auth import authenticate
from backend.tasks import do_import
from django.db.models import Sum, F, ExpressionWrapper, DecimalField
from django.http import HttpResponse


# Реализация импорта товаров
class PartnerUpdate(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        url = request.data.get('url')
        if request.user.type != 'shop':
            return Response(
                {'status': False, 'error': 'Только для магазинов'},
                status=status.HTTP_403_FORBIDDEN)
        if not url:
            return Response(
                {'status': False, 'error': 'Не указан url'},
                status=status.HTTP_400_BAD_REQUEST)
        do_import.delay(url, request.user.id)
        return Response({'status': True, 'message': 'Импорт запущен в фоне'})


# Регистрация
class RegisterView(APIView):
    def post(self, request):
        data = request.data
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        user_type = data.get('type')
        shop_name = data.get('shop_name')

        if not username or not email or not password:
            return Response(
                {'status': False,
                 'error': 'Email, имя пользователя и пароль обязательны'},
                status=status.HTTP_400_BAD_REQUEST)
        if User.objects.filter(username=data.get('username')).exists():
            return Response(
                {'status': False,
                 'Error': 'Пользователь с таким именем уже существует'},
                status=status.HTTP_400_BAD_REQUEST)
        user = User.objects.create_user(
            email=data.get('email'),
            username=data.get('username'),
            password=data.get('password'),
            type=user_type,
            is_active=False
        )
        if user_type == 'shop':
            if not shop_name:
                return Response(
                    {'status': False,
                     'error': 'Для типа shop необходимо указать shop_name'},
                    status=status.HTTP_400_BAD_REQUEST)
            Shop.objects.create(name=shop_name, user=user)

        new_user_registered.send(
            sender=self.__class__, user=user, request=request)
        return Response(
            {'status': True,
             'message': 'Письмо с подтверждением отправлено на почту'})


# Вход
class LoginView(APIView):
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        if not email or not password:
            return Response(
                {'status': False, 'error': 'Email и пароль обязательны'},
                status=status.HTTP_400_BAD_REQUEST)
        user = authenticate(request, username=email, password=password)
        if user is not None:
            if user.is_active:
                token, created = Token.objects.get_or_create(user=user)
                return Response(
                    {'status': True, 'token': token.key},
                    status=status.HTTP_200_OK)
            else:
                return Response(
                    {'status': False, 'error': 'Аккаунт не подтверждён'},
                    status=status.HTTP_403_FORBIDDEN)

        else:
            return Response(
                {'status': False, 'error': 'Неверные данные'},
                status=status.HTTP_401_UNAUTHORIZED)


# Подтверждение токена
class ConfirmEmailView(APIView):
    def post(self, request):
        if {'email', 'token'}.issubset(request.data):
            token = ConfirmEmailToken.objects.filter(
                user__email=request.data['email'],
                key=request.data['token']).first()
            if token:
                token.user.is_active = True
                token.user.save()
                token.delete()
                email_confirmed.send(sender=self.__class__, user=token.user)
                return Response({'status': True})
            else:
                return Response(
                    {'status': False,
                     'errors': 'Неправильно указан токен или email'})

        return Response(
            {'status': False,
             'errors': 'Не указаны все необходимые аргументы'})


# Список товаров
class ProductView(APIView):
    def get(self, request):
        products = ProductInfo.objects.select_related('product', 'shop').all()
        serializer = ProductInfoSerializer(products, many=True)
        return Response(serializer.data)


# Корзина (просмотр, добавление, удаление)
class BasketView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        basket = Order.objects.filter(
            user=request.user,
            status='basket').prefetch_related('items')
        return Response(OrderSerializer(basket, many=True).data)

    def post(self, request):
        product_info_id = request.data.get('product_info_id')
        quantity = request.data.get('quantity')
        if not product_info_id or not quantity:
            return Response(
                {'status': False,
                 'error': 'product_info_id и quantity обязательны'},
                status=status.HTTP_400_BAD_REQUEST)

        try:
            quantity = int(quantity)
            if quantity <= 0:
                raise ValueError
        except ValueError:
            return Response(
                {'status': False,
                 'error': 'Количество должно быть положительным числом'},
                status=status.HTTP_400_BAD_REQUEST)

        basket, _ = Order.objects.get_or_create(user=request.user,
                                                status='basket')
        try:
            product_info = ProductInfo.objects.get(id=product_info_id)
        except ProductInfo.DoesNotExist:
            return Response(
                {'status': False, 'error': 'Продукт не найден'},
                status=status.HTTP_400_BAD_REQUEST)

        OrderItem.objects.create(
            order=basket,
            product=product_info,
            shop=product_info.shop,
            quantity=quantity)
        return Response({'status': True})

    def delete(self, request):
        item_id = request.data.get('item_id')
        if not item_id:
            return Response(
                {'status': False, 'error': 'item_id обязателен'},
                status=status.HTTP_400_BAD_REQUEST)

        OrderItem.objects.filter(
            id=item_id,
            order__user=request.user,
            order__status='basket').delete()
        return Response({'status': True})


# Контакты (просмотр, добавление, удаление)
class ContactView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        contacts = Contact.objects.filter(user=request.user)
        return Response(ContactSerializer(contacts, many=True).data)

    def post(self, request):
        serializer = ContactSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response({'status': True})
        return Response({'status': False, 'error': serializer.errors})

    def delete(self, request):
        contact_id = request.data.get('contact_id')
        if not contact_id:
            return Response(
                {'status': False, 'error': 'contact_id обязателен'},
                status=status.HTTP_400_BAD_REQUEST)
        Contact.objects.filter(id=contact_id, user=request.user).delete()
        return Response({'status': True})


# Подтверждение заказа
class ConfirmOrderView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        order = Order.objects.filter(
            user=request.user, status='basket').first()
        if not order:
            return Response({'status': False, 'error': 'Корзина пуста'})

        contact_id = request.data.get('contact')
        contact = Contact.objects.filter(
            id=contact_id, user=request.user).first()
        if not contact:
            return Response({'status': False, 'Error': 'Контакт не найден'})
        contacts = request.user.contacts.all()
        has_address = contacts.filter(type='address').exists()
        has_phone = contacts.filter(type='phone').exists()
        if not has_address or not has_phone:
            return Response({
                'status': False,
                'error': 'Нужно указать адрес и телефон'
            }, status=status.HTTP_400_BAD_REQUEST)
        order.contact = contact
        order.status = 'new'
        order.save()
        new_order_status.send(
            sender=self.__class__,
            order=order,
        )
        return Response({'status': True})


# Просмотр заказов
class OrderListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        orders = Order.objects.filter(
            user=request.user).exclude(status='basket')
        return Response(OrderSerializer(orders, many=True).data)


# Включать/выключать принятие заказов
class PartnerOrderAvailableView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        try:
            shop = Shop.objects.get(user=user)
        except Shop.DoesNotExist:
            return Response({"error": "Shop not found"},
                            status=status.HTTP_404_NOT_FOUND)
        accepting = request.data.get('accepting_orders')
        if accepting is None:
            return Response({"error": "Field 'accepting_orders' is required"},
                            status=status.HTTP_400_BAD_REQUEST)
        shop.accepting_orders = bool(accepting)
        shop.save()
        return Response(
            {"status": "success",
             "accepting_orders": shop.accepting_orders})


# Получение заказов магазина
class PartnerOrdersView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        if request.user.type != 'shop':
            return Response(
                {'status': False, 'error': 'Только для магазинов'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Получаем все OrderItem, относящиеся к магазину текущего пользователя
        order_items = OrderItem.objects.filter(
            shop__user=request.user
        ).exclude(
            order__status='basket'
        ).annotate(
            item_sum=ExpressionWrapper(
                F('quantity') * F('product__price_rrc'),
                output_field=DecimalField(max_digits=10, decimal_places=2)
            )
        )

        # Суммируем сумму по каждому заказу
        order_sums = order_items.values('order').annotate(
            total_sum=Sum('item_sum')
        )

        order_ids = [entry['order'] for entry in order_sums]

        # Получаем заказы с нужными связями для сериализации
        orders = Order.objects.filter(
            id__in=order_ids
        ).select_related(
            'user'
        ).prefetch_related(
            'items__product__product__category',
            'items__product__parameters__parameter',
            'user__contacts'
        ).distinct()

        # Добавляем атрибут total_sum каждому заказу
        sums_map = {entry['order']: entry['total_sum'] for entry in order_sums}
        for order in orders:
            order.total_sum = sums_map.get(order.id, 0)

        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)


# Менять статус заказа
class PartnerState(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        if request.user.type != 'shop':
            return Response(
                {'status': False, 'error': 'Только для магазинов'},
                status=status.HTTP_403_FORBIDDEN
            )
        shop = request.user.shop
        serializer = ShopSerializer(shop)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        ALLOWED_STATUSES = ['new',
                            'confirmed',
                            'assembled',
                            'sent',
                            'delivered',
                            'cancelled']
        if request.user.type != 'shop':
            return Response(
                {'status': False, 'error': 'Только для магазинов'},
                status=status.HTTP_403_FORBIDDEN
            )
        try:
            shop = request.user.shop
        except Shop.DoesNotExist:
            return Response(
                {'status': False, 'error': 'Магазин не найден'},
                status=status.HTTP_404_NOT_FOUND
            )

        order_id = request.data.get('order_id')
        new_status = request.data.get('status')

        if not order_id or not new_status:
            return Response(
                {'status': False, 'error': 'order_id и status обязательны'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Проверяем, что заказ относится к этому магазину
        order_items = OrderItem.objects.filter(order_id=order_id, shop=shop)
        if not order_items.exists():
            return Response(
                {'status': False,
                 'error': 'Заказ не найден для данного магазина'},
                status=status.HTTP_404_NOT_FOUND
            )

        order = order_items.first().order
        order.status = new_status
        if new_status not in ALLOWED_STATUSES:
            return Response(
                {'status': False, 'error': 'Недопустимый статус заказа'},
                status=status.HTTP_400_BAD_REQUEST
                )
        order.save()

        # Отправляем сигнал о смене статуса (если есть)
        new_order_status.send(sender=self.__class__, order=order)

        return Response({'status': True,
                         'message': 'Статус заказа обновлён',
                         'order_status': order.status})


# Экспорт товаров
class PartnerExportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        if user.type != 'shop':
            return Response({'status': False,
                             'error': 'Только для магазинов'}, status=403)

        try:
            shop = Shop.objects.get(user=user)
        except Shop.DoesNotExist:
            return Response({'status': False, 'error': 'Магазин не найден'},
                            status=404)

        product_infos = ProductInfo.objects.filter(shop=shop).select_related(
            'product__category'
        ).prefetch_related('parameters__parameter')

        categories = {}
        goods = []

        for info in product_infos:
            product = info.product
            category = product.category
            categories[category.id] = category.name

            parameters = {
                param.parameter.name: param.value
                for param in info.parameters.all()
            }

            goods.append({
                'id': info.external_id,
                'name': product.name,
                'category': category.id,
                'model': info.model,
                'price': info.price,
                'price_rrc': info.price_rrc,
                'quantity': info.quantity,
                'parameters': parameters
            })

        data = {
            'shop': shop.name,
            'categories': [
                {'id': id, 'name': name} for id, name in categories.items()],
            'goods': goods
        }

        def clean_decimals(obj):
            if isinstance(obj, list):
                return [clean_decimals(i) for i in obj]
            elif isinstance(obj, dict):
                return {k: clean_decimals(v) for k, v in obj.items()}
            elif isinstance(obj, Decimal):
                return float(obj)
            return obj

        cleaned_data = clean_decimals(data)
        yaml_data = yaml.dump(cleaned_data, allow_unicode=True)

        return HttpResponse(yaml_data, content_type='text/yaml')
