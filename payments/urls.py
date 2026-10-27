from django.urls import path

from .views import PaymentDetailView, PaymentListCreateView

urlpatterns = [
    path('', PaymentListCreateView.as_view(), name='payments_list-create'),
    path('<int:payment_id>/', PaymentDetailView.as_view(), name='payment-detail'),
]