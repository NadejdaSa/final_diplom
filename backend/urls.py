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
    path('partner/update/', PartnerUpdate.as_view(), name='partner_update'),
    path('login/', LoginView.as_view(), name='login'),
    path('products/', ProductView.as_view(), name='products'),
    path('basket/', BasketView.as_view(), name='basket'),
    path('contacts/', ContactView.as_view(), name='contacts'),
]
