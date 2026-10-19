from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from decimal import Decimal

from users.models import User
from stores.models import Store
from products.models import Product, Category


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
        self.list_url = "/api/products/"
    def test_01(self):
        """Test authenticated user can create product"""

        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            self.list_url,
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

    def test_02(self):
        """Test unauthenticated user cannot create product"""

        response = self.client.post(
            self.list_url,
            data={
                "name": "Shirt",
                "description": "Cotton Shirt",
                "price": Decimal("59.90"),
                "stock": 10,
            },
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_03(self):
        """Test user without authenticated store cannot create product"""

        user_without_store = User.objects.create_user(
            email='salesman@gmail.com',
            first_name='Salesman',
            last_name='silva',
            password='password123',
        )
        self.client.force_authenticate(user=user_without_store)
        response = self.client.post(
            self.list_url,
            data={
                "name": "Shirt",
                "price": Decimal("59.90"),
                "stock": 10,
            },
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_04(self):
        """Test anyone can list active products"""

        Product.objects.create(
            store=self.store,
            name="Shirt",
            price=Decimal("59.90"),
            stock=10,
        )
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

    def test_05(self):
        """Test inactive products do not appear in list"""

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
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["name"], "Shirt")

    def test_06(self):
        """Test user cannot create product in another store"""

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
            self.list_url,
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

    def test_07(self):
        """Test inactive product cannot be retrieved"""

        inactive_product = Product.objects.create(
            store=self.store,
            name="pants",
            price=Decimal("59.90"),
            stock=5,
            is_active=False,
        )
        response = self.client.get(f"/api/products/{inactive_product.id}/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_08(self):
        """Test user without store cannot create product"""

        user_without_store = User.objects.create_user(
            email="peter@gmail.com",
            first_name="Peter",
            last_name="silva",
            password="password123",
        )
        self.client.force_authenticate(user=user_without_store)
        response = self.client.post(
            self.list_url,
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

    def test_09(self):
        """test create product with category"""

        category = Category.objects.create(name="Electronics")

        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            self.list_url,
            {
                "category": category.id,
                "name":"headset",
                "description": "Headset Test Other",
                "price":Decimal("199.90"),
                "stock":10
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        product = Product.objects.get(name="headset")
        self.assertEqual(product.category, category)

    def test_10(self):
        """test create product with invalid category"""
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            self.list_url,
            {
                "category": 9999,
                "name":"headset",
                "description": "Headset Test Other",
                "price":Decimal("199.90"),
                "stock":10
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Product.objects.filter(name="headset").exists())

    def test_11(self):
        """test filter products by category"""

        category_electronics = Category.objects.create(name="Electronics")
        category_books = Category.objects.create(name="Books")

        Product.objects.create(
            store=self.store,
            category= category_electronics,
            name="headset",
            description="Headset Test Other",
            price=Decimal("199.90"),
            stock=10,
        )
        Product.objects.create(
            store=self.store,
            category= category_books,
            name="Books Python",
            description="Learn Python",
            price=Decimal("50.90"),
            stock=5,
        )
        response = self.client.get(
            self.list_url,
            {"category":category_electronics.id},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["name"], "headset")

    def test_12(self):
        """test filter products excluded inactive products"""

        category = Category.objects.create(name="Electronics")

        Product.objects.create(
            store=self.store,
            category= category,
            name="Product active",
            description="Headset Test Other",
            price=Decimal("199.90"),
            stock=10,
            is_active=True,
        )
        Product.objects.create(
            store=self.store,
            category= category,
            name="Product inactive",
            description="Headset Test Other",
            price=Decimal("199.90"),
            stock=10,
            is_active=False,
        )
        response = self.client.get(
            self.list_url,
            {"category":category.id}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        product_name = [item["name"] for item in response.data['results']]
        self.assertIn("Product active", product_name)
        self.assertNotIn("Product inactive", product_name)

    def test_13(self):
        """test filter products with invalid category"""

        response = self.client.get(
            self.list_url,
            {"category":"acb"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("category", response.data)

    def test_14(self):
        """test filter products with not existent category"""

        response = self.client.get(
            self.list_url,
            {"category":9999},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 0)

    def test_15(self):
        """test product list returns paginated response"""

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("count", response.data)
        self.assertIn("next", response.data)
        self.assertIn("previous", response.data)
        self.assertIn("results", response.data)

    def test_16(self):
        """test product list returns maximum ten products per page"""
        Product.objects.filter(store=self.store).update(is_active=False)

        for i in range(12):
            Product.objects.create(
                store=self.store,
                name=f"Product {i}",
                description=f"Product test {i}",
                price=Decimal("199.90"),
                stock=10,
            )
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 12)
        self.assertEqual(len(response.data["results"]), 10)
        self.assertIsNotNone(response.data["next"])
        self.assertIsNone(response.data["previous"])

    def test_17(self):
        """test searching for products by name"""

        Product.objects.create(
            store=self.store,
            name="Shirt Blue",
            description="Product test shirt",
            price=Decimal("40.90"),
            stock=10,
        )
        Product.objects.create(
            store=self.store,
            name="Shots",
            description="Product test shots",
            price=Decimal("199.90"),
            stock=10,
        )
        response = self.client.get(self.list_url, {"search": "Shirt"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["name"], "Shirt Blue")

    def test_18(self):
        """test order products by price descending"""

        Product.objects.create(
            store=self.store,
            name="Product expensive",
            description="Product expensive test",
            price=Decimal("199.90"),
            stock=10,
        )
        Product.objects.create(
            store=self.store,
            name="Product cheap",
            description="Product cheap test",
            price=Decimal("20.90"),
            stock=10,
        )
        response = self.client.get(self.list_url, {"ordering": "price"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        products = response.data["results"]
        self.assertEqual(products[0]["name"], "Product cheap")
        self.assertEqual(products[1]["name"], "Product expensive")

    def test_19(self):
        """test search products without results"""

        Product.objects.create(
            store=self.store,
            name="Product cheap",
            description="Product cheap test",
            price=Decimal("20.90"),
            stock=10,
        )
        response = self.client.get(self.list_url, {"search":"ProductNonexistentXYZ"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)
        self.assertEqual(response.data["results"], [])

    def test_20(self):
        """test filter products by min price"""

        Product.objects.create(
            store=self.store,
            name="Product expensive",
            description="Product expensive test",
            price=Decimal("199.90"),
            stock=10,
        )
        Product.objects.create(
            store=self.store,
            name="Product cheap",
            description="Product cheap test",
            price=Decimal("20.90"),
            stock=10,
        )
        response = self.client.get(self.list_url, {"min_price":"50"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["name"], "Product expensive")

    def test_21(self):
        """test filter products by max price"""

        Product.objects.create(
            store=self.store,
            name="Product expensive",
            description="Product expensive test",
            price=Decimal("199.90"),
            stock=10,
        )
        Product.objects.create(
            store=self.store,
            name="Product cheap",
            description="Product cheap test",
            price=Decimal("20.90"),
            stock=10,
        )
        response = self.client.get(self.list_url, {"max_price":"50"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["name"], "Product cheap")

    def test_22(self):
        """test filter products by price range"""

        for name, price in [
            ("Cheap Product", "20.00"),
            ("Medium Product", "50.00"),
            ("Expensive Product", "100.00"),
        ]:
            Product.objects.create(
                store=self.store,
                name=name,
                price=Decimal(price),
                stock=10,
            )
        response = self.client.get(self.list_url, {"min_price":"30", "max_price":"60"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["name"], "Medium Product")

    def test_23(self):
        """test filter products with invalid price"""

        response = self.client.get(self.list_url, {"min_price":"invalid"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

class CategoryViewTest(APITestCase):
    def setUp(self):
        self.category = Category.objects.create(
            name="Electronics",
            description="Electronics Test Other",
        )
        self.list_url = reverse("category-list")
        self.detail_url = reverse("category-detail", kwargs={"pk": self.category.pk})

    def test_01(self):
        """test: anyone can list categories"""

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["name"], "Electronics")

    def test_02(self):
        """test anyone can recover the category"""

        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Electronics")

    def test_03(self):
        """test anonymous user cannot create category"""

        response = self.client.post(
            self.list_url,
            {
                "name": "Books",
                "description": "Books Test Other",
            },
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_04(self):
        """test regular user cannot create category"""

        user = User.objects.create_user(
            email='salesman@email.com',
            password='password123',
            first_name='ana',
            last_name='silva',
        )
        self.client.force_authenticate(user=user)

        response = self.client.post(
            self.list_url,
            {
                "name": "Books",
                "description": "Books Test Other",
            },
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Category.objects.filter(name="Books").exists())

    def test_05(self):
        """test admin user can create category"""

        admin_user = User.objects.create_superuser(
            email='admin@email.com',
            password='password123',
            first_name='admin',
            last_name='silva',
        )
        self.client.force_authenticate(user=admin_user)

        response = self.client.post(
            self.list_url,
            {
                "name": "Books",
                "description": "Books Test Other",
            },
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Category.objects.filter(name="Books").exists())