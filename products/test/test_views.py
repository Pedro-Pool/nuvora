from django.test import TestCase
from rest_framework import status, viewsets
from rest_framework.test import APIClient
from decimal import Decimal

from users.models import User
from stores.models import Store
from products.models import Product

class ProductViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.user = User.objects.create_user(
            email='saleswoman@gmail.com',
            first_name='Salesman',
            last_name='silva',
            password='password123',
        )
        self.store = Store.objects.create(
            owner=self.user,
            name='My Store',
            description='My Store Test',
        )
    def test_authenticated_user_can_create_product(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            "/api/products/",
            data={
                "name": "Shirt",
                "description": "Cotton Shirt",
                "price": Decimal("59.90"),
                "stock": 10,
            },
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Product.objects.filter(store=self.store, name="Shirt").exists())

    def test_unauthenticated_user_cannot_create_product(self):
        response = self.client.post(
            "/api/products/",
            data={
                "name": "Shirt",
                "description": "Cotton Shirt",
                "price": Decimal("59.90"),
                "stock": 10,
            },
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_without_authenticated_store_cannot_create_product(self):
        user_without_store = User.objects.create_user(
            email='salesman@gmail.com',
            first_name='Salesman',
            last_name='silva',
            password='password123',
        )
        self.client.force_authenticate(user=user_without_store)
        response = self.client.post(
            "/api/products/",
            data={
                "name": "Shirt",
                "price": Decimal("59.90"),
                "stock": 10,
            },
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_anyone_can_list_active_products(self):
        Product.objects.create(
            store=self.store,
            name="Shirt",
            price=Decimal("59.90"),
            stock=10,
        )
        response = self.client.get("/api/products/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_inactive_products_do_not_appear_in_list(self):
        Product.objects.create(
            store=self.store,
            name="Shirt",
            price=Decimal("59.90"),
            stock=10,
            is_active=True,
        )
        Product.objects.create(
            store=self.store,
            name="pants",
            price=Decimal("59.90"),
            stock=5,
            is_active=False,
        )
        response = self.client.get("/api/products/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["name"], "Shirt")

    def test_user_cannot_create_product_in_another_store(self):
        other_user = User.objects.create_user(
            email='saleswoman13@gmail.com',
            first_name='Ana',
            last_name='silva',
            password='password123',
        )
        other_store = Store.objects.create(
            owner=other_user,
            name='My Store Other',
            description='My Store Test Other',
        )
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            "/api/products/",
            data={
                "store": other_store.id,
                "name": "Pants",
                "description": "Pants Test Other",
                "price": Decimal("59.90"),
                "stock": 5,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        product = Product.objects.get(name="Pants")
        self.assertEqual(product.store, self.store)
        self.assertNotEqual(product.store, other_store)

    def test_inactive_product_cannot_be_retrieved(self):
        inactive_product = Product.objects.create(
            store=self.store,
            name="pants",
            price=Decimal("59.90"),
            stock=5,
            is_active=False,
        )
        response = self.client.get(f"/api/products/{inactive_product.id}/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_without_store_cannot_create_product(self):
        user_without_store = User.objects.create_user(
            email="peter@gmail.com",
            first_name="Peter",
            last_name="silva",
            password="password123",
        )
        self.client.force_authenticate(user=user_without_store)
        response = self.client.post(
            "/api/products/",
            data={
                "name": "Pants",
                "description": "Pants Test Other",
                "price": Decimal("59.90"),
                "stock": 5,
            },
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(Product.objects.filter(name="Pants").exists())
