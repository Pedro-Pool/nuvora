from decimal import Decimal
from unittest.mock import patch

from django.db.models import Model
from rest_framework import status
from rest_framework.test import APITestCase
from django.db import DatabaseError

from cart.models import Cart, CartItem
from orders.models import Order, OrderItem
from products.models import Product
from users.models import User
from stores.models import Store

class OrderCreateViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            first_name="Test",
            last_name="User",
            email="test@email.com",
            password="password123"
        )
        self.client.force_authenticate(user=self.user)

        self.store = Store.objects.create(
            owner=self.user,
            name='salesman store test',
            description='salesman store description',
        )

        self.cart = Cart.objects.create(user=self.user)

        self.product = Product.objects.create(
            store=self.store,
            name="Test Product",
            description="Test Description",
            price=Decimal("25.00"),
            stock=10,
            is_active=True,
        )
        self.url = "/api/orders/"

    def test_01(self):
        """test cannot create order with empty cart"""

        response = self.client.post(self.url, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Order.objects.count(), 0)

    def test_02(self):
        """test cannot create order with insufficient stock"""

        CartItem.objects.create(cart=self.cart, product=self.product, quantity=11)

        response = self.client.post(self.url, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Order.objects.count(), 0)

        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 10)

        self.assertEqual(CartItem.objects.filter(cart=self.cart).count(), 1)

    def test_03(self):
        """test create order successfully"""

        CartItem.objects.create(cart=self.cart, product=self.product, quantity=2)
        response = self.client.post(self.url, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(OrderItem.objects.count(), 1)

        order = Order.objects.get()
        self.assertEqual(order.total_amount, Decimal("50.00"))
        self.assertEqual(order.items.get().quantity, 2)
        self.assertEqual(order.items.get().unit_price, Decimal("25.00"))

        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 8)
        self.assertEqual(CartItem.objects.filter(cart=self.cart).count(), 0)

    @patch("orders.views.OrderItem.objects.create", side_effect=DatabaseError("Simulated database failure"))
    def test_04(self, mock_create):
        """rolls back order and stock on failure"""

        CartItem.objects.create(cart=self.cart, product=self.product, quantity=2)

        with self.assertRaises(DatabaseError):
            response = self.client.post(self.url, format="json")

        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(OrderItem.objects.count(), 0)

        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 10)
        self.assertEqual(CartItem.objects.filter(cart=self.cart).count(), 1)

    def test_05(self):
        """User can list their own orders"""

        order = Order.objects.create(
            user=self.user,
            total_amount=Decimal("50.00"),
        )
        OrderItem.objects.create(
            order=order,
            product=self.product,
            product_name=self.product.name,
            unit_price=self.product.price,
            quantity=1)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], order.id)
        self.assertEqual(len(response.data[0]["items"]), 1)

    def test_06(self):
        """User cannot see orders belonging to another user"""

        other_user = User.objects.create_user(
            first_name="Test",
            last_name="User",
            email="other@email.com",
            password="password123"
        )
        Order.objects.create(
            user=other_user,
            total_amount=Decimal("100.00"),
        )
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_07(self):
        """User can retrieve their own order details"""
        order = Order.objects.create(
            user=self.user,
            total_amount=Decimal("50.00"),
        )
        OrderItem.objects.create(
            order=order,
            product=self.product,
            product_name=self.product.name,
            unit_price=self.product.price,
            quantity=2
        )
        response = self.client.get(f'{self.url}{order.id}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], order.id)
        self.assertEqual(response.data["total_amount"], "50.00")
        self.assertEqual(len(response.data["items"]), 1)

    def test_08(self):
        """User cannot retrieve another user's order"""

        other_user = User.objects.create_user(
            first_name="Test",
            last_name="User",
            email="other@email.com",
            password="password123"
        )
        order = Order.objects.create(
            user=other_user,
            total_amount=Decimal("100.00"),
        )
        response = self.client.get(f'{self.user}{order.id}/')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_09(self):
        """Requesting a non-existent order return 404"""

        response = self.client.get(f"{self.url}9999/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_10(self):
        """Cancelling a pending order restores product stock"""

        order = Order.objects.create(
            user=self.user,
            total_amount=Decimal("50.00"),
            status=Order.Status.PENDING,
        )
        OrderItem.objects.create(
            order=order,
            product=self.product,
            product_name=self.product.name,
            unit_price=self.product.price,
            quantity=2
        )
        self.product.stock = 8
        self.product.save(update_fields=["stock"])

        response = self.client.post(f'{self.url}{order.id}/cancel/', format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        order.refresh_from_db()
        self.product.refresh_from_db()

        self.assertEqual(order.status, Order.Status.CANCELED)
        self.assertEqual(self.product.stock, 10)

    def test_11(self):
        """Cancelling an order twice must not restore stock twice"""

        order = Order.objects.create(
            user=self.user,
            total_amount=Decimal("50.00"),
            status=Order.Status.CANCELED,
        )
        OrderItem.objects.create(
            order=order,
            product=self.product,
            product_name=self.product.name,
            unit_price=self.product.price,
            quantity=2
        )
        self.product.stock = 10
        self.product.save(update_fields=["stock"])

        response = self.client.post(f'{self.url}{order.id}/cancel/', format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 10)

    def test_12(self):
        """A user cannot cancel another user's order"""

        other_user = User.objects.create_user(
            first_name="Test",
            last_name="User",
            email="other@email.com",
            password="password123"
        )
        order = Order.objects.create(
            user=other_user,
            total_amount=Decimal("50.00"),
            status=Order.Status.PENDING,
        )
        response = self.client.post(f'{self.url}{order.id}/cancel/', format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.PENDING)

    def test_13(self):
        """An already shipped order cannot be canceled here"""

        order = Order.objects.create(
            user=self.user,
            total_amount=Decimal("50.00"),
            status=Order.Status.SHIPPED,
        )
        response = self.client.post(f'{self.url}{order.id}/cancel/', format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.SHIPPED)

    def test_14(self):
        """A delivered order cannot be canceled"""

        order = Order.objects.create(
            user=self.user,
            total_amount=Decimal("50.00"),
            status=Order.Status.DELIVERED,
        )
        response = self.client.post(f'{self.url}{order.id}/cancel/', format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.DELIVERED)