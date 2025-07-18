from django.urls import path

from backend.views import RegisterView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
]
