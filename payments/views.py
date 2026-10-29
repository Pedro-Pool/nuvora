from django.db import transaction
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from orders.models import Order
from .models import Payment
from .serializers import PaymentSerializer
from .service import AsaasError, create_asaas_checkout

class PaymentListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        payments = (Payment.objects
        .filter(order__user=request.user)
        .select_related("order")
        .order_by("-created_at")
        )
        serializer = PaymentSerializer(payments, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        order_id = request.data.get('order')

        if not order_id:
            return Response({"detail": "The order field is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            order_id = int(order_id)
        except (ValueError, TypeError):
            return Response({"detail": "Invalid ID"}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            try:
                order = (Order.objects.select_for_update().get(pk=order_id, user=request.user))
            except Order.DoesNotExist:
                return Response({"detail": "Order not found"}, status=status.HTTP_404_NOT_FOUND)

            if order.status == Order.Status.CANCELED:
                return Response({"detail": "Cannot pay for a cancelled order"}, status=status.HTTP_400_BAD_REQUEST)

            if Payment.objects.filter(order=order, status=Payment.Status.APPROVED).exists():
                return Response({"detail": "This order has already been paid"}, status=status.HTTP_400_BAD_REQUEST)

            if Payment.objects.filter(order=order, status=Payment.Status.PENDING).exists():
                return Response({"detail": "A pending payments  already  exist for this order"}, status=status.HTTP_409_CONFLICT)

            payment = Payment.objects.create(
                order=order,
                amount=order.total_amount,
                currency="BRL",
                provider=Payment.Provider.ASAAS,
                status=Payment.Status.PENDING,
            )

            try:
                checkout = create_asaas_checkout(payment)
            except AsaasError:
                payment.status = Payment.Status.FAILED
                payment.save(update_fields=["status", "updated_at"])

                return Response(
                    {"detail": "Unable to create the payment checkout"},
                    status=status.HTTP_502_BAD_GATEWAY)

            serializer = PaymentSerializer(payment)
            return Response(
                {
                    **serializer.data,
                    "checkout_url": checkout["checkout_url"],
                },
                status=status.HTTP_201_CREATED)

class PaymentDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, payment_id):
        try:
            payment = (Payment.objects.select_related("order").get(pk=payment_id, order__user=request.user))
        except Payment.DoesNotExist:
            return Response({"detail": "Payment not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = PaymentSerializer(payment)
        return Response(serializer.data, status=status.HTTP_200_OK)

class CheckoutReturnView(APIView):
    permission_classes = []
    def get(self, request):
        return HttpResponse("Checkout response received ""The payment status needs to be confirmed")

class CheckoutCancelView(APIView):
    permission_classes = []

    def get(self, request):
        return HttpResponse("Checkout canceled or interrupted""The payment status has not been changed")
