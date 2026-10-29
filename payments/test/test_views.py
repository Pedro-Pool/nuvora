from decimal import Decimal

from rest_framework import status
from rest_framework.test import APITestCase
from unittest.mock import patch

from orders.models import Order
from payments.models import Payment
from users.models import User

class PaymentAPITest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            first_name='John',
            last_name='Doe',
            email='payment@email.com',
            password='password123'
        )
        self.client.force_authenticate(user=self.user)

        self.order = Order.objects.create(
            user=self.user,
            total_amount=Decimal("99.90"),
        )
        self.url = "/api/payments/"

        self.checkout_patcher = patch(
            "payments.views.create_asaas_checkout",
            return_value={
                "checkout_id":"chk_test123",
                "checkout_url":"https://example.com/checkout",
            }
        )
        self.mock_create_checkout = self.checkout_patcher.start()
        self.addCleanup(self.checkout_patcher.stop)

    def test_01(self):
        """Should create pending payment"""

        response = self.client.post(self.url, {"order": self.order.id}, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], Payment.Status.PENDING)
        self.assertEqual(Decimal(response.data['amount']), Decimal("99.90"))

    def test_02(self):
        """Payment amount comes from orderr"""
        response = self.client.post(
            self.url,
            {"order": self.order.id, "amount": "1.00"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Decimal(response.data["amount"]), Decimal("99.90"))

    def test_03(self):
        """Cannot create payment for other users order"""

        other_user = User.objects.create_user(
            first_name='Other',
            last_name='Doe',
            email='other@email.com',
            password='password123'
        )
        other_order = Order.objects.create(
            user=other_user,
            total_amount=Decimal("50.00"),
        )
        response = self.client.post(self.url, {"order": other_order.id}, format='json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(Payment.objects.all().count(), 0)

    def test_04(self):
        """List only own payments"""

        Payment.objects.create(
            order=self.order,
            amount=Decimal("99.90"),
        )
        other_user = User.objects.create_user(
            first_name='Other',
            last_name='Doe',
            email='other@email.com',
            password='password123'
        )
        other_order = Order.objects.create(
            user=other_user,
            total_amount=Decimal("50.00"),
        )
        Payment.objects.create(
            order=other_order,
            amount=Decimal("50.00"),
        )
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['order'], self.order.id)

    def test_05(self):
        """Get down payment detail"""

        payment = Payment.objects.create(
            order=self.order,
            amount=Decimal("99.90"),
        )
        response = self.client.get(f"{self.url}{payment.id}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], payment.id)

    def test_06(self):
        """Cannot get another user's payment detail"""

        other_user = User.objects.create_user(
            first_name='Other',
            last_name='Doe',
            email='other@email.com',
            password='password123'
        )
        other_order = Order.objects.create(
            user=other_user,
            total_amount=Decimal("50.00"),
        )
        payment = Payment.objects.create(
            order=other_order,
            amount=Decimal("50.00"),
        )
        response = self.client.get(f"{self.url}{payment.id}/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_07(self):
        """Cannot create duplicate pending payment"""

        first_response = self.client.post(
            self.url,
            {"order":self.order.id},
            format='json'
        )
        second_response = self.client.post(
            self.url,
            {"order":self.order.id},
            format='json'
        )
        self.assertEqual(first_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second_response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(Payment.objects.filter(order=self.order, status=Payment.Status.PENDING).count(), 1)

    def test_08(self):
        """Can retry after failed payment"""

        Payment.objects.create(
            order=self.order,
            amount=self.order.total_amount,
            status=Payment.Status.FAILED,
        )
        response = self.client.post(
            self.url,
            {"order":self.order.id},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Payment.objects.filter(order=self.order, status=Payment.Status.PENDING).count(), 1)

    def test_09(self):
        """Client cannot approve payment"""

        response = self.client.post(
            self.url,
            {
                "order":self.order.id,
                "status":Payment.Status.APPROVED,
                "amount":"1.00",
                "provider": Payment.Provider.MANUAL
            },
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        payment = Payment.objects.get(order=self.order)

        self.assertEqual(payment.status, Payment.Status.PENDING)
        self.assertEqual(payment.amount, self.order.total_amount)