from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from django.db import close_old_connections
from rest_framework.test import APIClient, APITransactionTestCase

from cart.models import Cart, CartItem
from orders.models import Order
from products.models import Product
from stores.models import Store
from users.models import User


class OrderStockConcurrencyTest(APITransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.user_a = User.objects.create_user(
            email="buyer_a@example.com",
            first_name="Buyer",
            last_name="A",
            password="password123",
        )

        self.user_b = User.objects.create_user(
            email="buyer_b@example.com",
            first_name="Buyer",
            last_name="B",
            password="password123",
        )

        self.store_owner = User.objects.create_user(
            email="seller@example.com",
            first_name="Seller",
            last_name="Test",
            password="password123",
        )

        self.store = Store.objects.create(
            owner=self.store_owner,
            name="Test Store",
            description="Concurrency test",
        )

        self.product = Product.objects.create(
            store=self.store,
            name="Last Product",
            description="Only one unit available",
            price="50.00",
            stock=1,
        )

        for user in [self.user_a, self.user_b]:
            cart = Cart.objects.create(user=user)

            CartItem.objects.create(
                cart=cart,
                product=self.product,
                quantity=1,
            )

        self.url = "/api/orders/"

    def make_order_request(self, user, barrier):
        close_old_connections()

        try:
            client = APIClient()
            client.force_authenticate(user=user)

            barrier.wait(timeout=10)

            response = client.post(self.url, {}, format="json")

            return response.status_code

        finally:
            close_old_connections()

    def test_01(self):
        """Test only one user can buy the last product"""

        barrier = Barrier(2)

        with ThreadPoolExecutor(max_workers=2) as executor:
            future_a = executor.submit(
                self.make_order_request,
                self.user_a,
                barrier,
            )

            future_b = executor.submit(
                self.make_order_request,
                self.user_b,
                barrier,
            )

            status_a = future_a.result(timeout=20)
            status_b = future_b.result(timeout=20)

        self.product.refresh_from_db()

        self.assertEqual(
            sorted([status_a, status_b]),
            [201, 400],
        )

        self.assertEqual(self.product.stock, 0)
        self.assertEqual(Order.objects.count(), 1)