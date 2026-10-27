from decimal import Decimal

from django.test import TestCase

from orders.models import Order
from payments.models import Payment
from stores.models import Store
from users.models import User

class PaymentTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            first_name="John",
            last_name="Doe",
            email="payment@email.com",
            password="password123",
        )
        self.order = Order.objects.create(
            user=self.user,
            total_amount=Decimal("99.90"),
        )
    def test_01(self):
        """Should create a payment"""

        payment = Payment.objects.create(
            order=self.order,
            amount=Decimal("99.90"),
            currency="BRL",
        )
        self.assertEqual(payment.status, Payment.Status.PENDING)
        self.assertEqual(payment.amount, Decimal("99.90"))
        self.assertEqual(payment.currency, "BRL")
        self.assertIsNotNone(payment.reference)

    def test_02(self):
        """test payment has unique reference"""

        first_payment = Payment.objects.create(
            order=self.order,
            amount=Decimal("99.90"),
        )
        second_payment = Payment.objects.create(
            order=self.order,
            amount=Decimal("99.90"),
            status=Payment.Status.FAILED,
        )
        self.assertNotEqual(first_payment.reference, second_payment.reference)