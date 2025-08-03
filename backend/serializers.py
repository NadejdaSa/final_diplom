from rest_framework import serializers
from backend.models import Contact, Order, OrderItem, User, Product, \
    ProductInfo, Shop, Category, Parameter, ProductParameter


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'password']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            username=validated_data.get('username', '')
        )
        return user


class ShopSerializer(serializers.ModelSerializer):
    categories = serializers.StringRelatedField(many=True, read_only=True)

    class Meta:
        model = Shop
        fields = ['id', 'name', 'url', 'categories']


class CategorySerializer(serializers.ModelSerializer):
    shops = ShopSerializer(many=True, read_only=True)

    class Meta:
        model = Category
        fields = ['id', 'name', 'shops']


class ProductSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)

    class Meta:
        model = Product
        fields = ['id', 'name', 'category']


class ProductInfoSerializer(serializers.ModelSerializer):
    product = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all())
    shop = serializers.PrimaryKeyRelatedField(queryset=Shop.objects.all())
    product_detail = ProductSerializer(source='product', read_only=True)
    shop_detail = ShopSerializer(source='shop', read_only=True)

    class Meta:
        model = ProductInfo
        fields = ['id',
                  'product',
                  'shop',
                  'model',
                  'quantity',
                  'price',
                  'price_rrc',
                  'product_detail',
                  'shop_detail']


class ParameterSerializer(serializers.ModelSerializer):

    class Meta:
        model = Parameter
        fields = ['id', 'name']


class ProductParameterSerializer(serializers.ModelSerializer):

    class Meta:
        model = ProductParameter
        fields = ['id', 'product_info', 'parameter', 'value']


class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductInfoSerializer(read_only=True)
    shop = ShopSerializer(read_only=True)

    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'quantity', 'shop']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    user = UserSerializer(read_only=True)
    total_sum = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'user', 'dt', 'status', 'items', 'total_sum']


class ContactSerializer(serializers.ModelSerializer):

    class Meta:
        model = Contact
        fields = ['id', 'type', 'value']
