from django.urls import path, include
from django.contrib import admin
from backend.views import PartnerExportView, PartnerOrdersView, PartnerState, \
    RegisterView, ConfirmEmailView, LoginView, ProductView, BasketView, \
    ContactView, OrderListView, ConfirmOrderView, PartnerUpdate, \
    PartnerOrderAvailableView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('confirm-email/', ConfirmEmailView.as_view(), name='confirm-email'),
    path('partner/update/', PartnerUpdate.as_view(), name='partner_update'),
    path('login/', LoginView.as_view(), name='login'),
    path('product-list/', ProductView.as_view(), name='products'),
    path('basket/', BasketView.as_view(), name='basket'),
    path('contacts/', ContactView.as_view(), name='contacts'),
    path('orders/my/', OrderListView.as_view(), name='my-orders'),
    path('order/confirm/', ConfirmOrderView.as_view(), name='order-confirm'),
    path('password_reset/', include('django_rest_passwordreset.urls')),
    path('partner/orders/availability/', PartnerOrderAvailableView.as_view(),
         name='partner_order_availability'),
    path('partner/orders/', PartnerOrdersView.as_view(),
         name='partner_orders'),
    path('partner/state/', PartnerState.as_view(), name='partner_state'),
    path('partner/export/', PartnerExportView.as_view(),
         name='partner_export'),
]
