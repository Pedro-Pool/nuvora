from django.test import TestCase
from decimal import Decimal
from django.db import transaction, IntegrityError

from cart.models import Cart, CartItem
from stores.models import Store
from products.models import Product
from users.models import User


class CartModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="buyer@example.com",
            first_name="Test",
            last_name="User",
            password="password123"
        )
        self.store_owner = User.objects.create_user(
            email="seller@example.com",
            first_name="Owner",
            last_name="User",
            password="password123"
        )
        self.store = Store.objects.create(
            owner=self.store_owner,
            name="Store test",
            description="Store for carts test",
        )
        self.product = Product.objects.create(
            store=self.store,
            name="Product test",
            description="Product for cart test",
            price=Decimal(100),
            stock=10,
        )
        self.cart = Cart.objects.create(user=self.user)

    def test_01(self):
        """Test cart belongs to user"""

        self.assertEqual(self.cart.user, self.user)

    def test_02(self):
        """Test user can have only one cart"""

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Cart.objects.create(user=self.user)

    def test_03(self):
        """Test cart item has quantity"""

        item = CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=2,
        )
        self.assertEqual(item.quantity, 2)
        self.assertEqual(item.cart, self.cart)
        self.assertEqual(item.product, self.product)

    def test_04(self):
        """Test same product cannot be added twice  as  separate items"""

        CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=1,
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                CartItem.objects.create(
                    cart=self.cart,
                    product=self.product,
                    quantity=2,
                )

    def test_05(self):
        """Test cart item quantity must be positive"""

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                CartItem.objects.create(
                    cart=self.cart,
                    product=self.product,
                    quantity=0,
                )

    def test_06(self):
        """Test deleting cart deletes its items"""

        CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=1,
        )
        self.cart.delete()

        self.assertEqual(CartItem.objects.count(), 0)

    def test_07(self):
        """Test product with cart item cannot be deleted"""

        CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=1,
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.product.delete()
