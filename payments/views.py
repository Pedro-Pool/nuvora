from decimal import Decimal

from django.db import transaction
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from orders.models import Order
from .models import Payment
from .serializers import PaymentSerializer

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
                provider=Payment.Provider.MANUAL,
                status=Payment.Status.PENDING,
            )
            serializer = PaymentSerializer(payment)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

class PaymentDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, payment_id):
        try:
            payment = (Payment.objects.select_related("order").get(pk=payment_id, order__user=request.user))
        except Payment.DoesNotExist:
            return Response({"detail": "Payment not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = PaymentSerializer(payment)
        return Response(serializer.data, status=status.HTTP_200_OK)
