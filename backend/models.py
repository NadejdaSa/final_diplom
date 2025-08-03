from django.db import models
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser, \
    PermissionsMixin
from django_rest_passwordreset.tokens import get_token_generator


# Create your models here.
class UserManager(BaseUserManager):
    """
    Миксин для управления пользователями
    """
    use_in_migrations = True

    def _create_user(self, email, password, type, **extra_fields):
        if not email:
            raise ValueError('Email обязателен для создания пользователя.')
        email = self.normalize_email(email)
        extra_fields.setdefault('username', email.split('@')[0])
        user = self.model(email=email, type=type, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_user(self, email, password=None, type='buyer',  **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, type, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Суперпользователь должен иметь is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Суперпользователь должен иметь \
                             is_superuser=True')
        return self._create_user(email, password, type='shop', **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Стандартная модель пользователей
    """
    USER_TYPES = (
        ('shop', 'Магазин'),
        ('buyer', 'Покупатель'),
    )
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=150, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    type = models.CharField(max_length=10, choices=USER_TYPES, default='buyer')
    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email


# Модель магазина
class Shop(models.Model):
    name = models.CharField(max_length=200)
    url = models.URLField(null=True)
    user = models.OneToOneField(User,
                                blank=True, null=True,
                                on_delete=models.CASCADE)
    accepting_orders = models.BooleanField(default=True)

    def __str__(self):
        return self.name


# Модель категории товара
class Category(models.Model):
    name = models.CharField(max_length=200)
    shops = models.ManyToManyField(Shop, related_name='categories')

    def __str__(self):
        return self.name


# Модель товара
class Product(models.Model):
    name = models.CharField(max_length=200)
    category = models.ForeignKey(Category, related_name='products',
                                 on_delete=models.CASCADE)

    def __str__(self):
        return self.name


# Информация о товаре в конкретном магазине
class ProductInfo(models.Model):
    product = models.ForeignKey(Product, related_name='product_infos',
                                on_delete=models.CASCADE)
    shop = models.ForeignKey(Shop, related_name="product_infos",
                             on_delete=models.CASCADE)
    model = models.CharField(max_length=100, blank=True, null=True)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    price_rrc = models.DecimalField(max_digits=10, decimal_places=2)
    external_id = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.product.name} в {self.shop.name} — {self.price} руб."


# Параметры (характеристики) товара
class Parameter(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


# Значения параметров товара
class ProductParameter(models.Model):
    product_info = models.ForeignKey(ProductInfo, related_name='parameters',
                                     on_delete=models.CASCADE)
    parameter = models.ForeignKey(Parameter, related_name='product_parameters',
                                  on_delete=models.CASCADE)
    value = models.CharField(max_length=100)

    class Meta:
        unique_together = ('product_info', 'parameter')

    def __str__(self):
        return f"{self.parameter.name}: {self.value}"


# Заказ
class Order(models.Model):
    user = models.ForeignKey(User, related_name='orders',
                             on_delete=models.CASCADE)
    dt = models.DateTimeField(auto_now_add=True)
    STATUS_CHOICES = (
        ('new', 'New'),
        ('confirmed', 'Confirmed'),
        ('assembled', 'Assembled'),
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES,
                              default='new')

    def __str__(self):
        return f'Order #{self.id} - {self.user}'


# Позиции заказа (конкретные товары в заказе)
class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items',
                              on_delete=models.CASCADE)
    product = models.ForeignKey(ProductInfo, related_name='order_items',
                                on_delete=models.CASCADE)
    shop = models.ForeignKey(Shop, related_name='order_items',
                             on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()

    def __str__(self):
        return f'{self.product.product.name} x {self.quantity}'


# Контактная информация пользователя
class Contact(models.Model):
    CONTACT_TYPES = (
        ('email', 'Email'),
        ('phone', 'Phone'),
        ('address', 'Address'),
    )
    type = models.CharField(max_length=20, choices=CONTACT_TYPES)
    user = models.ForeignKey(User, related_name='contacts',
                             on_delete=models.CASCADE)
    value = models.CharField(max_length=200)

    def __str__(self):
        return f"{self.type}:{self.value}"


# Токен подтверждения email
class ConfirmEmailToken(models.Model):
    objects = models.manager.Manager()

    @staticmethod
    def generate_key():
        return get_token_generator().generate_token()

    user = models.ForeignKey(
        User, related_name='confirm_email_tokens', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    key = models.CharField(("Key"), max_length=64, db_index=True, unique=True)

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = self.generate_key()
        return super(ConfirmEmailToken, self).save(*args, **kwargs)

    def __str__(self):
        return f"Email confirmation token for {self.user.email}"
