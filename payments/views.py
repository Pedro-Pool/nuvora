import json

from django.db import transaction
from django.http import HttpResponse
from django.conf import settings
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from orders.models import Order
from .models import Payment, AsaasWebhookEvent
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

@method_decorator(csrf_exempt, name='dispatch')
class AsaasWebhookEventView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        expected_token = getattr(
            settings,
            "ASAAS_WEBHOOK_TOKEN",
            "",
        )
        received_token = request.headers.get("asaas-access-token","")

        if not expected_token or received_token != expected_token:
            return Response({"detail": "Invalid webhook token"}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            payload = json.loads(request.body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return Response({"detail":"Invalid JSON"}, status=status.HTTP_400_BAD_REQUEST)

        if not isinstance(payload, dict):
            return Response({"detail":"JSON body must be an object"}, status=status.HTTP_400_BAD_REQUEST)

        event_id = payload.get("id")
        event_type = payload.get("event")

        if not isinstance(event_id, str) or not event_id.strip():
            return Response({"detail":"Missing or invalid event ID"}, status=status.HTTP_400_BAD_REQUEST)

        if not isinstance(event_type, str) or not event_type.strip():
            return Response({"detail": "Missing or invalid event type"}, status=status.HTTP_400_BAD_REQUEST)

        if event_type != "CHECKOUT_PAID":
            return Response({"detail": "Event ignored"}, status=status.HTTP_200_OK)

        checkout = payload.get("checkout") or {}

        if not isinstance(checkout, dict):
            return Response({"detail": "Missing or invalid checkout object"}, status=status.HTTP_400_BAD_REQUEST)

        checkout_id = checkout.get("id")

        if not isinstance(checkout_id, str):
            return Response({"detail": "Missing or invalid checkout ID"}, status=status.HTTP_400_BAD_REQUEST)

        if checkout.get("status") != "PAID":
            return Response({"detail": "Checkout is not marked as paid"}, status=status.HTTP_400_BAD_REQUEST)

        with (transaction.atomic()):
            try:
                payment_lookup = Payment.objects.only("id", "order_id").get(
                    provider=Payment.Provider.ASAAS, provider_checkout_id=checkout_id
                )
            except Payment.DoesNotExist:
                return Response({"detail": "Payment not found"}, status=status.HTTP_404_NOT_FOUND)

            try:
                order = Order.objects.select_for_update().get(pk=payment_lookup.order_id)
            except Order.DoesNotExist:
                return Response({"detail": "Order not found"}, status=status.HTTP_404_NOT_FOUND)

            try:
                payment = (
                    Payment.objects.
                    select_for_update()
                    .get(
                        pk=payment_lookup.pk,
                        provider=Payment.Provider.ASAAS,
                        provider_checkout_id=checkout_id
                    )
                )
            except Payment.DoesNotExist:
                return Response({"detail": "Payment not found"}, status=status.HTTP_404_NOT_FOUND)

            event, created = AsaasWebhookEvent.objects.get_or_create(
                event_id=event_id,
                defaults={"event_type":event_type}
            )

            event = AsaasWebhookEvent.objects.select_for_update().get(pk=event.pk)

            if event.event_type != event_type:
                return Response({"detail":"Event detail mismatch"}, status=status.HTTP_400_BAD_REQUEST)

            if event.processed:
                return Response({"detail":"Event already processed"}, status=status.HTTP_200_OK)

            if payment.status not in(
                Payment.Status.PENDING,
                Payment.Status.APPROVED,
            ):
                return Response({"detail":"Payment is not eligible for approval"}, status=status.HTTP_409_CONFLICT)

            if order.status == Order.Status.CANCELED:
                return Response({"detail":"Order is canceled"}, status=status.HTTP_409_CONFLICT)

            if payment.status == Payment.Status.PENDING:
                payment.status = Payment.Status.APPROVED
                payment.save(update_fields=["status", "updated_at"])

            if order.status == Order.Status.PENDING:
                order.status = Order.Status.CONFIRMED
                order.save(update_fields=["status", "updated_at"])

            event.processed = True
            event.processed_at = timezone.now()
            event.save(update_fields=["processed", "processed_at"])

        return Response({"detail":"Webhook processed"}, status=status.HTTP_200_OK)
