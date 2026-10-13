from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from users.models import User
from stores.models import Store

class StoreViewsTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="vendedor@email.com",
            first_name="Pedro",
            last_name="Silva",
            password="password123",
        )
        self.client.force_authenticate(user=self.user)

    def test_authenticated_user_can_create_store(self):
        response = self.client.post(
            "/api/stores/",
            {
                "name": "My Store",
                "description": "Store Test",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Store.objects.filter(user=self.user).exists())
        self.assertEqual(response.data["name"], "My Store")

    def test_authenticated_user_cannot_create_store(self):

