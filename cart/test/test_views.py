from rest_framework import status
from rest_framework.test import APITestCase
from decimal import Decimal

from cart.models import Cart, CartItem
from products.models import Product
from users.models import User
from stores.models import Store


class CartItemViewsTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='buyer@example.com',
            first_name='buyer',
            last_name='silva',
            password='password123',
        )
        self.other_user = User.objects.create_user(
            email='other@example.com',
            first_name='other',
            last_name='silva',
            password='password456',
        )
        self.store_owner = User.objects.create_user(
            email='salesman@example.com',
            first_name='salesman',
            last_name='silva',
            password='password123!',
        )
        self.store = Store.objects.create(
            owner=self.store_owner,
            name='salesman store test',
            description='salesman store description',
        )
        self.product = Product.objects.create(
            store=self.store,
            name='salesman product',
            description='salesman product description',
            price=Decimal("100.00"),
            stock=10,
        )
        self.cart = Cart.objects.create(user=self.user)
        self.item = CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=2,
        )

        self.client.force_authenticate(user=self.user)

    def test_01(self):
        """Test patch updates quantity"""

        response = self.client.patch(
            f'/api/cart/items/{self.item.id}/',
            {"quantity": 4},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.item.refresh_from_db()
        self.assertEqual(self.item.quantity, 4)
    def test_02(self):
        """Test patch rejects quantity above stock"""

        response = self.client.patch(
            f'/api/cart/items/{self.item.id}/',
            {"quantity": 11},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.item.refresh_from_db()
        self.assertEqual(self.item.quantity, 2)

    def test_03(self):
        """Test patch rejects zero quantity"""

        response = self.client.patch(
            f'/api/cart/items/{self.item.id}/',
            {"quantity": 0},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_04(self):
        """test delete removes item"""

        response = self.client.delete(
            f'/api/cart/items/{self.item.id}/'
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(CartItem.objects.filter(pk=self.item.id).exists())

    def test_05(self):
        """test user cannot update another user's item"""

        other_cart = Cart.objects.create(user=self.other_user)
        other_item = CartItem.objects.create(cart=other_cart, product=self.product, quantity=1)

        response = self.client.patch(
            f'/api/cart/items/{other_item.id}/',
            {"quantity": 3},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        other_item.refresh_from_db()
        self.assertEqual(other_item.quantity, 1)

    def test_06(self):
        """test user cannot delete another user's item"""

        other_cart = Cart.objects.create(user=self.other_user)
        other_item = CartItem.objects.create(cart=other_cart, product=self.product, quantity=1)

        response = self.client.delete(
            f'/api/cart/items/{other_item.id}/'
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(CartItem.objects.filter(pk=other_item.id).exists())

    def test_07(self):
        """test patch updates cart updated at"""

        original_updated_at = self.cart.updated_at

        response = self.client.patch(
            f'/api/cart/items/{self.item.id}/',
            {"quantity": 4},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.cart.refresh_from_db()
        self.assertGreater(self.cart.updated_at, original_updated_at)
