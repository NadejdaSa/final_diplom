from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from backend.models import User, Shop, Category, Product, ProductInfo, \
    Parameter, ProductParameter, Order, OrderItem, \
    Contact, ConfirmEmailToken

from backend.signals import new_order_status


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """
    Панель управления пользователями
    """
    model = User

    fieldsets = (
        (None, {'fields': ('email', 'password', 'type')}),
        ('Personal info', {'fields': ('username',)}),
        ('Permissions', {
            'fields': (
                'is_active',
                'is_staff',
                'is_superuser',
                'groups',
                'user_permissions'),
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    list_display = ('email', 'type', 'is_staff', 'is_active', 'get_shop_name')

    def get_shop_name(self, obj):
        # попытка получить название магазина, связанного с пользователем
        try:
            return obj.shop.name
        except Shop.DoesNotExist:
            return '-'

    get_shop_name.short_description = 'Магазин'


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    """
    Панель управления магазинами.
    Отвечает за отображение, поиск и редактирование магазинов.
    """
    list_display = ('name', 'url', 'user')
    search_fields = ('name', )


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """
    Панель управления категориями товаров.
    Отвечает за отображение, поиск и редактирование категорий.
    """
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """
    Панель управления товарами.
    Отвечает за отображение, фильтрацию и поиск товаров.
    """
    list_display = ('name', 'category')
    list_filter = ('category',)
    search_fields = ('name',)


@admin.register(ProductInfo)
class ProductInfoAdmin(admin.ModelAdmin):
    """
    Панель управления информацией о товарах (цена, количество и т.д.).
    Отвечает за отображение, фильтрацию и поиск.
    """
    list_display = ('product', 'shop', 'price', 'quantity', 'external_id')
    list_filter = ('shop', 'product')
    search_fields = ('product__name', 'shop__name')


@admin.register(Parameter)
class ParameterAdmin(admin.ModelAdmin):
    """
    Панель управления параметрами товаров.
    Отвечает за отображение и поиск параметров.
    """
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(ProductParameter)
class ProductParameterAdmin(admin.ModelAdmin):
    """
    Панель управления значениями параметров товаров.
    Отвечает за отображение, фильтрацию и поиск.
    """
    list_display = ('product_info', 'parameter', 'value')
    list_filter = ('parameter',)
    search_fields = ('parameter__name', 'value')


class OrderItemInline(admin.TabularInline):
    """
    Встроенный (inline) админ-класс для редактирования позиций заказов внутри заказа.
    """
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """
    Панель управления заказами.
    Позволяет просматривать, фильтровать, искать и редактировать заказы.
    Отслеживает изменения статуса заказа и отправляет сигнал.
    """
    list_display = ('id', 'user', 'status', 'dt')
    list_filter = ('status', 'dt')
    search_fields = ('user__email',)
    inlines = [OrderItemInline]
    list_editable = ('status',)

    def save_model(self, request, obj, form, change):
        if change:
            old_status = Order.objects.get(pk=obj.pk).status
            if old_status != obj.status:
                super().save_model(request, obj, form, change)
                new_order_status.send(sender=self.__class__, order=obj)
                return
        super().save_model(request, obj, form, change)

    def save_queryset(self, request, queryset):
        for obj in queryset:
            old_status = Order.objects.get(pk=obj.pk).status
            if old_status != obj.status:
                new_order_status.send(sender=self.__class__, order=obj)
        super().save_queryset(request, queryset)


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    """
    Панель управления позициями заказов.
    Позволяет просматривать, фильтровать и искать позиции заказов.
    """
    list_display = ('order', 'product', 'quantity', 'shop')
    list_filter = ('order', 'shop')
    search_fields = ('product__product__name', 'shop__name')


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    """
    Панель управления контактами пользователей.
    Позволяет просматривать, фильтровать и искать контакты.
    """
    list_display = ('user', 'type', 'value')
    list_filter = ('type',)
    search_fields = ('value', 'user__email')


@admin.register(ConfirmEmailToken)
class ConfirmEmailTokenAdmin(admin.ModelAdmin):
    """
    Панель управления токенами подтверждения email.
    Отображает информацию о токенах и позволяет их искать.
    """
    list_display = ('user', 'key', 'created_at',)
    readonly_fields = ('key', 'created_at',)
    search_fields = ('user__email', 'key')
