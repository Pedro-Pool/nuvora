from django.urls import path

from .views import OrderCreateView, OrderDetailView, OrderCanceledView

urlpatterns = [
    path('', OrderCreateView.as_view(), name='order-list-create'),
    path('<int:order_id>/cancel/', OrderCanceledView.as_view(), name='order-cancel'),
    path('<int:order_id>/', OrderDetailView.as_view(), name='order-detail'),
]