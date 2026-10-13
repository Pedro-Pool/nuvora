from django.test import TestCase
from decimal import Decimal
from users.models import User
from stores.models import Store
from products.models import Product

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

    def test_create_product(self):
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

    def test_product_belongs_to_store(self):
        product = Product.objects.create(
            store=self.store,
            name="shirt",
            price="85.99",
            stock=10,
        )
        self.assertEqual(product.store, self.store)
        self.assertIn(product, self.store.products.all())

    def test_product_description_is_optional(self):
        product = Product.objects.create(
            store=self.store,
            name="shirt",
            price="85.99",
            stock=10,
        )
        self.assertEqual(product.description, "")