import json
import threading

from django.db import close_old_connections
from django.test import override_settings, TestCase, TransactionTestCase
from rest_framework import status
from rest_framework.test import APIClient
from decimal import Decimal

from config.settings import ASAAS_WEBHOOK_TOKEN
from orders.models import Order
from payments.models import Payment, AsaasWebhookEvent
from users.models import User


@override_settings(ASAAS_WEBHOOK_TOKEN='test_webhook_token')
class AsaasWebhookTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = "/api/payments/webhook/asaas/"

        self.user = User.objects.create_user(
            first_name="Test",
            last_name="User",
            email="usertest@email.com",
            password="password123"
        )
        self.order = Order.objects.create(
            user=self.user,
            total_amount=Decimal("90.00"),
            status=Order.Status.PENDING,
        )
        self.payment = Payment.objects.create(
            order=self.order,
            amount=Decimal("90.00"),
            provider=Payment.Provider.ASAAS,
            status=Payment.Status.PENDING,
            provider_checkout_id="chk_test123"
        )
        self.payload = {
            "id":"evt_test123",
            "event":"CHECKOUT_PAID",
            "checkout":{
                "id":"chk_test123",
                "status":"PAID",
            },
        }

        self.headers = {
            "HTTP_ASAAS_ACCESS_TOKEN":"test_webhook_token",
        }

    def test_01(self):
        """Webhook approves payment and confirms orders"""

        response = self.client.post(
            self.url,
            data=json.dumps(self.payload),
            content_type="application/json",
            **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.payment.refresh_from_db()
        self.order.refresh_from_db()

        self.assertEqual(self.payment.status, Payment.Status.APPROVED)
        self.assertEqual(self.order.status, Order.Status.CONFIRMED)

        event = AsaasWebhookEvent.objects.get(event_id="evt_test123")
        self.assertTrue(event.processed)
        self.assertIsNotNone(event.processed_at)

    def test_02(self):
        """Duplicate webhook is not processed twice"""

        first_response = self.client.post(
            self.url,
            data=json.dumps(self.payload),
            content_type="application/json",
            **self.headers
        )
        second_response = self.client.post(
            self.url,
            data=json.dumps(self.payload),
            content_type="application/json",
            **self.headers
        )

        event = AsaasWebhookEvent.objects.get(
            event_id="evt_test123"
        )

        self.assertTrue(event.processed)
        self.assertIsNotNone(event.processed_at)

        self.assertEqual(first_response.status_code, status.HTTP_200_OK)
        self.assertEqual(second_response.status_code, status.HTTP_200_OK)

        self.assertEqual(AsaasWebhookEvent.objects.filter(event_id="evt_test123").count(), 1)

        self.payment.refresh_from_db()
        self.order.refresh_from_db()

        self.assertEqual(self.payment.status, Payment.Status.APPROVED)
        self.assertEqual(self.order.status, Order.Status.CONFIRMED)

    def test_03(self):
        """Webhook reject request with an invalid token"""

        response = self.client.post(
            self.url,
            data=json.dumps(self.payload),
            content_type="application/json",
            HTTP_ASAAS_ACCESS_TOKEN="invalid_token",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        self.assertFalse(AsaasWebhookEvent.objects.filter(event_id="evt_test123").exists())

    def test_04(self):
        """Webhook does not approve payment for a canceled order"""

        self.order.status = Order.Status.CANCELED
        self.order.save(update_fields=["status"])

        response = self.client.post(
            self.url,
            data=json.dumps(self.payload),
            content_type="application/json",
            **self.headers
        )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

        self.payment.refresh_from_db()
        self.order.refresh_from_db()

        self.assertEqual(self.payment.status, Payment.Status.PENDING)
        self.assertEqual(self.order.status, Order.Status.CANCELED)

    def test_05(self):
        """Webhook ignore unsupported event types"""

        payload = {
            **self.payload,
            "event":"CHECKOUT_CREATED",
        }
        response = self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
            **self.headers
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(AsaasWebhookEvent.objects.filter(event_id="evt_test123").exists())

        self.payment.refresh_from_db()
        self.order.refresh_from_db()

        self.assertEqual(self.payment.status, Payment.Status.PENDING)
        self.assertEqual(self.order.status, Order.Status.PENDING)

    def test_06(self):
        """Webhook does not approve a checkout with different status"""

        payload = {
            **self.payload,
            "checkout":{
                **self.payload['checkout'],
                "status":"PENDING",
            }
        }
        response = self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
            **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.payment.refresh_from_db()
        self.order.refresh_from_db()

        self.assertEqual(self.payment.status, Payment.Status.PENDING)
        self.assertEqual(self.order.status, Order.Status.PENDING)
        self.assertFalse(AsaasWebhookEvent.objects.filter(event_id="evt_test123").exists())

    def test_07(self):
        """Webhook reject a checkout that does not exist locally"""

        payload = {
            **self.payload,
            "checkout":{
                **self.payload['checkout'],
                "id":"chk_nonexist",
            }
        }
        response = self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
            **self.headers
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        self.payment.refresh_from_db()
        self.order.refresh_from_db()

        self.assertEqual(self.payment.status, Payment.Status.PENDING)
        self.assertEqual(self.order.status, Order.Status.PENDING)
        self.assertFalse(AsaasWebhookEvent.objects.filter(event_id="evt_test123").exists())

    def test_08(self):
        """Different events for the same checkout do not duplicate approval"""

        second_payload = {
            **self.payload,
            "id":"evt_test456"
        }

        first_response = self.client.post(
            self.url,
            data=json.dumps(self.payload),
            content_type="application/json",
            **self.headers
        )
        second_response = self.client.post(
            self.url,
            data=json.dumps(second_payload),
            content_type="application/json",
            **self.headers
        )

        self.assertEqual(first_response.status_code, status.HTTP_200_OK)
        self.assertEqual(second_response.status_code, status.HTTP_200_OK)

        self.payment.refresh_from_db()
        self.order.refresh_from_db()

        self.assertEqual(self.payment.status, Payment.Status.APPROVED)
        self.assertEqual(self.order.status, Order.Status.CONFIRMED)

        self.assertEqual(AsaasWebhookEvent.objects.filter(processed=True).count(), 2)

@override_settings(ASAAS_WEBHOOK_TOKEN="test_webhook_token")
class AsaasWebhookConcurrencyTest(TransactionTestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = "/api/payments/webhook/asaas/"

        self.user = User.objects.create_user(
            first_name="Test",
            last_name="User",
            email="concurrency@email.com",
            password="password123"
        )
        self.order = Order.objects.create(
            user=self.user,
            total_amount=Decimal("90.00"),
            status=Order.Status.PENDING,
        )
        self.payment = Payment.objects.create(
            order=self.order,
            amount=Decimal("90.00"),
            provider=Payment.Provider.ASAAS,
            status=Payment.Status.PENDING,
            provider_checkout_id="chk_concurrency123"
        )

    def test_01(self):
        """Concurrent duplicate webhook"""

        payload = {
            "id": "evt_concurrency123",
            "event": "CHECKOUT_PAID",
            "checkout": {
                "id": "chk_concurrency123",
                "status": "PAID",
            }
        }
        headers = {
            "HTTP_ASAAS_ACCESS_TOKEN": "test_webhook_token",
        }

        barrier = threading.Barrier(2)
        results = []
        errors = []

        def send_webhook():
            close_old_connections()

            try:
                client = APIClient()
                barrier.wait(timeout=10)

                response = client.post(
                    self.url,
                    data=json.dumps(payload),
                    content_type="application/json",
                    **headers
                )
                results.append(response.status_code)
            except Exception as e:
                errors.append(e)
            finally:
                close_old_connections()

        threads = [
            threading.Thread(target=send_webhook),
            threading.Thread(target=send_webhook)
        ]

        for t in threads:
            t.start()

        for t in threads:
            t.join(timeout=20)

        self.assertFalse(any(t.is_alive() for t in threads), "Webhook threads did not finish in time")

        self.assertEqual(errors, [])
        self.assertEqual(len(results), 2)

        self.assertEqual(results.count(status.HTTP_200_OK), 2)

        self.payment.refresh_from_db()
        self.order.refresh_from_db()

        self.assertEqual(self.payment.status, Payment.Status.APPROVED)
        self.assertEqual(self.order.status, Order.Status.CONFIRMED)

        self.assertEqual(AsaasWebhookEvent.objects.filter(event_id="evt_concurrency123").count(), 1)

        event = AsaasWebhookEvent.objects.get(
            event_id="evt_concurrency123"
        )
        self.assertTrue(event.processed)
        self.assertIsNotNone(event.processed_at)
