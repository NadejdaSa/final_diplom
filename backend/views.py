from django.forms import ValidationError
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.authtoken.models import Token
from .serializers import CategorySerializer, ContactSerializer, OrderSerializer, OrderItemSerializer, ParameterSerializer, ProductSerializer, ProductInfoSerializer, ProductParameterSerializer, ShopSerializer, UserSerializer
from .models import Category, ConfirmEmailToken, Contact, Order, OrderItem, Parameter, Product, ProductInfo, ProductParameter, Shop, User
from django.core.validators import URLValidator
from requests import get
from backend.signals import new_user_registered
from django.contrib.auth import authenticate
import yaml


# Реализация импорта товаров
class PartnerUpdate(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        if request.user.type != 'shop':
            return Response({'status': False, 'error': 'Только для магазинов'}, status=status.HTTP_403_FORBIDDEN)

        url = request.data.get('url')
        if not url:
            return Response({'status': False, 'error': 'Не указан url'}, status=status.HTTP_400_BAD_REQUEST)

        validate_url = URLValidator()
        try:
            validate_url(url)
        except ValidationError as e:
            return Response({'status': False, 'error': f'Некорректный URL: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            response = get(url)
            response.raise_for_status()
            data = yaml.safe_load(response.content)
        except Exception as e:
            return Response({'status': False, 'error': f'Ошибка загрузки yaml: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)

        shop_name = data.get('shop')
        if not shop_name:
            return Response({'status': False,
                                 'error': 'Не указан магазин'}, status=status.HTTP_400_BAD_REQUEST)
        shop, _ = Shop.objects.get_or_create(name=data['shop'],
                                             user_id=request.user.id)

        for category in data.get('categories', []):
            category_obj, _ = Category.objects.get_or_create(id=category['id'],
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

        return Response({'status': True})


# Регистрация
class RegisterView(APIView):
    def post(self, request):
        data = request.data
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        if not username or not email or not password:
            return Response({'status': False,
                             'error': 'Email, имя пользователя и пароль обязательны'}, status=status.HTTP_400_BAD_REQUEST)
        if User.objects.filter(username=data.get('username')).exists():
            return Response({'status': False, 'Error': 'Пользователь с таким именем уже существует'}, status=status.HTTP_400_BAD_REQUEST)
        user = User.objects.create_user(
            email=data.get('email'),
            username=data.get('username'),
            password=data.get('password'),
            is_active=False
        )
        new_user_registered.send(sender=self.__class__, user=user, request=request)
        return Response({'status': True, 'message': 'Письмо с подтверждением отправлено на почту'})


# Вход
class LoginView(APIView):
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        if not email or not password:
            return Response({'status': False, 'error': 'Email и пароль обязательны'}, status=status.HTTP_400_BAD_REQUEST)
        user = authenticate(request, username=email, password=password)
        if user is not None:
            if user.is_active:
                token, created = Token.objects.get_or_create(user=user)
                return Response({'status': True, 'token': token.key}, status=status.HTTP_200_OK)
            else:
                return Response({'status': False, 'error': 'Аккаунт не подтверждён'}, status=status.HTTP_403_FORBIDDEN)

        else:
            return Response({'status': False, 'error': 'Неверные данные'},
                        status=status.HTTP_401_UNAUTHORIZED)


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
                return Response({'status': True})
            else:
                return Response({'status': False, 'errors': 'Неправильно указан токен или email'})

        return Response({'status': False, 'errors': 'Не указаны все необходимые аргументы'})


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
        basket = Order.objects.filter(user=request.user,
                                      status='basket').prefetch_related('ordered_items')
        return Response(OrderSerializer(basket, many=True).data)

    def post(self, request):
        product_info_id = request.data.get('product_info_id')
        quantity = request.data.get('quantity')
        if not product_info_id or not quantity:
            return Response({'status': False, 'error': 'product_info_id и quantity обязательны'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            quantity = int(quantity)
            if quantity <= 0:
                raise ValueError
        except ValueError:
            return Response({'status': False, 'error': 'Количество должно быть положительным числом'}, status=status.HTTP_400_BAD_REQUEST)

        basket, _ = Order.objects.get_or_create(user=request.user,
                                                status='basket')
        OrderItem.objects.create(order=basket, product_info_id=product_info_id, quantity=quantity)
        return Response({'status': True})

    def delete(self, request):
        item_id = request.data.get('item_id')
        if not item_id:
            return Response({'status': False, 'error': 'item_id обязателен'}, status=status.HTTP_400_BAD_REQUEST)

        OrderItem.objects.filter(id=item_id, order__user=request.user, order__status='basket').delete()
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
            return Response({'status': False, 'error': 'contact_id обязателен'}, status=status.HTTP_400_BAD_REQUEST)
        Contact.objects.filter(id=contact_id, user=request.user).delete()
        return Response({'status': True})


# Подтверждение заказа
class ConfirmOrderView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        order = Order.objects.filter(user=request.user, status='basket').first()
        if not order:
            return Response({'status': False, 'error': 'Корзина пуста'})

        contact_id = request.data.get('contact')
        contact = Contact.objects.filter(id=contact_id, user=request.user).first()
        if not contact:
            return Response({'status': False, 'Error': 'Контакт не найден'})

        order.contact = contact
        order.status = 'new'
        order.save()
        return Response({'status': True})


# Просмотр заказов
class OrderListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        orders = Order.objects.filter(user=request.user).exclude(status='basket')
        return Response(OrderSerializer(orders, many=True).data)


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer


# Просмотр магазинов
class ShopViewSet(viewsets.ModelViewSet):
    queryset = Shop.objects.all()
    serializer_class = ShopSerializer


# Просмотр категорий
class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer


class ProductInfoViewSet(viewsets.ModelViewSet):
    queryset = ProductInfo.objects.all()
    serializer_class = ProductInfoSerializer


class ParameterViewSet(viewsets.ModelViewSet):
    queryset = Parameter.objects.all()
    serializer_class = ParameterSerializer


class ProductParameterViewSet(viewsets.ModelViewSet):
    queryset = ProductParameter.objects.all()
    serializer_class = ProductParameterSerializer


class OrderItemViewSet(viewsets.ModelViewSet):
    queryset = OrderItem.objects.all()
    serializer_class = OrderItemSerializer


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
