from django.urls import path

from .views import PaymentDetailView, PaymentListCreateView, CheckoutReturnView, CheckoutCancelView

urlpatterns = [
    path('', PaymentListCreateView.as_view(), name='payments_list-create'),
    path('<int:payment_id>/', PaymentDetailView.as_view(), name='payment-detail'),
    path('checkout/success/', CheckoutReturnView.as_view(), name='checkout-success'),
    path('checkout/cancel/', CheckoutCancelView.as_view(), name='checkout-cancel'),
    path('checkout/expired/', CheckoutCancelView.as_view(), name='checkout-expired'),
]