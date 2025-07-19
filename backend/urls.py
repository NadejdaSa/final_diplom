from django.urls import path, include
from rest_framework.routers import DefaultRouter
from backend.views import *

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'shops', ShopViewSet)
router.register(r'categories', CategoryViewSet)
router.register(r'products', ProductViewSet)
router.register(r'product_info', ProductInfoViewSet)
router.register(r'parameters', ParameterViewSet)
router.register(r'product_parameters', ProductParameterViewSet)
router.register(r'order_items', OrderItemViewSet)
router.register(r'orders', OrderViewSet)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('', include(router.urls)),
]
