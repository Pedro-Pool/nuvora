from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import RegisterView, MeView, LoginView

urlpatterns = [
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='toke_refresh'),
    path('users/me/', MeView.as_view(), name='me'),
]