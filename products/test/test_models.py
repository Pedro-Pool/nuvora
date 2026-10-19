from django.test import TestCase
from decimal import Decimal
from users.models import User
from stores.models import Store
from products.models import Product, Category


class ProductTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="salesman@email.com",
            first_name="salesman",
            last_name="silva",
            password="password132"
        )

        self.store = Store.objects.create(
            owner=self.user,
            name="My Store",
            description="Store test",
        )

    def test_01(self):
        """Test create product"""

        product = Product.objects.create(
            store=self.store,
            name="shirt",
            description="Shirt test",
            price=Decimal("85.99"),
            stock=10,
        )
        self.assertEqual(product.name, "shirt")
        self.assertEqual(product.price, Decimal("85.99"))
        self.assertEqual(product.stock, 10)
        self.assertTrue(product.is_active)

    def test_02(self):
        """Test product belongs to store"""

        product = Product.objects.create(
            store=self.store,
            name="shirt",
            price="85.99",
            stock=10,
        )
        self.assertEqual(product.store, self.store)
        self.assertIn(product, self.store.products.all())

    def test_03(self):
        """Test product description is optional"""

        product = Product.objects.create(
            store=self.store,
            name="shirt",
            price="85.99",
            stock=10,
        )
        self.assertEqual(product.description, "")

    def test_04(self):
        """A product can belong to a category"""

        user = User.objects.create_user(
            email="category@email.com",
            password="passwordSecurity",
            first_name="category",
            last_name="test",
        )
        store = Store.objects.create(
            owner=user,
            name="My Store test",
        )
        category = Category.objects.create(name="Electronics")

        product = Product.objects.create(
            store=store,
            category=category,
            name="headset",
            description="Headset test",
            price=Decimal("85.99"),
            stock=10,
        )
        self.assertEqual(product.category, category)
        self.assertIn(product, category.products.all())

class CategoryModelTest(TestCase):
    def test_01(self):
        """Test create category"""

        category = Category.objects.create(
            name="My Category",
            description="My Description",
        )
        self.assertEqual(category.name, "My Category")
        self.assertEqual(category.description, "My Description")
        self.assertIsNotNone(category.id)

    def test_02(self):
        """The test category name must be unique"""

        Category.objects.create(name="My Category")

        with self.assertRaises(Exception):
            Category.objects.create(name="My Category")

    def test_03(self):
        """The test category (str) returns the name"""

        category = Category.objects.create(name="Books")

        self.assertEqual(str(category), "Books")
