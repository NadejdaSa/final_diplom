from django.forms import ValidationError
from django.http import JsonResponse
from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import generics, viewsets, status
from rest_framework.permissions import IsAuthenticated
from .serializers import CategorySerializer, ContactSerializer, OrderItemSerializer, OrderSerializer, ParameterSerializer, ProductInfoSerializer, ProductParameterSerializer, ProductSerializer, ShopSerializer, UserSerializer
from .models import Category, Contact, Order, OrderItem, Parameter, Product, ProductInfo, ProductParameter, Shop, User
from django.core.validators import URLValidator
from requests import get
from django.contrib.auth import authenticate, login
import yaml
# Create your views here.


class PartnerUpdate(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Необходима авторизация'}, status=403)
        if request.user.type != 'shop':
            return JsonResponse({'Status': False, 'Error': 'Только для магазинов'}, status=403)

        url = request.data.get('url')
        if not url:
            return JsonResponse({'Status': False, 'Error': 'Не указан url'}, status=400)

        validate_url = URLValidator()
        try:
            validate_url(url)
        except ValidationError as e:
            return JsonResponse({'Status': False, 'Error': f'Некорректный URL: {str(e)}'}, status=400)

        try:
            response = get(url)
            response.raise_for_status()
            data = yaml.safe_load(response.content)
        except Exception as e:
            return JsonResponse({'Status': False, 'Error': f'Ошибка загрузки yaml: {str(e)}'}, status=400)

        shop_name = data.get('shop')
        if not shop_name:
            return JsonResponse({'Status': False,
                                 'Error': 'Не указан магазин'}, status=400)
        shop, _ = Shop.objects.get_or_create(name=data['shop'],
                                             user_id=request.user.id)

        for category in data['categories']:
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
                ProductParameter.objects.create(product_info_id=product_info.id,
                                                parameter_id=parameter.id,
                                                value=value)

        return JsonResponse({'Status': True})


# Вход
class LoginView(APIView):
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        user = authenticate(username=username, password=password)
        if user is not None:
            login(request, user)
            return Response({'status': True}, status=status.HTTP_200_OK)
        return Response({'status': False, 'Error': 'Неверные данные'},
                        status=status.HTTP_401_UNAUTHORIZED)


# Регистрация
class RegisterView(APIView):
    def post(self, request):
        data = request.data
        if User.objects.filter(username=data.get('username')).exists():
            return Response({'status': False, 'Error': 'Пользователь с таким именем уже существует'}, status= 400)
        user = User.objects.create_user(
            email=data.get('email'),
            username=data.get('username'),
            password=data.get('password'),
        )
        user.save()
        return Response({'status': True})


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
                                      state='basket').prefetch_related('ordered_items')
        return Response(OrderSerializer(basket, many=True).data)

    def post(self, request):
        product_info_id = request.data.get('product_info_id')
        quantity = request.data.get('quantity')
        basket, _ = Order.objects.get_or_create(user=request.user,
                                                state='basket')
        OrderItem.objects.create(order=basket, product_info_id=product_info_id, quantity=quantity)
        return Response({'status': True})

    def delete(self, request):
        item_id = request.data.get('item_id')
        OrderItem.objects.filter(id=item_id, order__user=request.user, order__state='basket').delete()
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
        return Response({'Status': False, 'Error': serializer.errors})

    def delete(self, request):
        contact_id = request.data.get('contact_id')
        Contact.objects.filter(id=contact_id, user=request.user).delete()
        return Response({'status': True})


# Подтверждение заказа
class ConfirmOrderView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        order = Order.objects.filter(user=request.user, state='basket').first()
        if not order:
            return Response({'status': False, 'Error': 'Корзина пуста'})

        contact_id = request.data.get('contact')
        contact = Contact.objects.filter(id=contact_id, user=request.user).first()
        if not contact:
            return Response({'status': False, 'Error': 'Контакт не найден'})

        order.contact = contact
        order.state = 'new'
        order.save()
        return Response({'status': True})


# Просмотр заказов
class OrderListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        orders = Order.objects.filter(user=request.user).exclude(state='basket')
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
