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

    def test_01(self):
        """Test authenticated user can create store"""

        response = self.client.post(
            "/api/stores/",
            {
                "name": "My Store",
                "description": "Store Test",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Store.objects.filter(owner=self.user).exists())
        self.assertEqual(response.data["name"], "My Store")

    def test_02(self):
        """Test authenticated user cannot create store"""

        self.client.force_authenticate(user=None)
        response = self.client.post(
            "/api/stores/",
            {"name": "Unauthorized store",},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_03(self):
        """Test user can retrieve own store"""

        Store.objects.create(
            owner=self.user,
            name="My Store",
            description="Store Test",
        )
        response = self.client.get("/api/stores/me/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "My Store")

    def test_04(self):
        """Test user without store gets 404"""

        response = self.client.get("/api/stores/me/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_05(self):
        """Test user cannot create second store"""

        Store.objects.create(
            owner=self.user,
            name="My Store",
        )
        response = self.client.post(
            "/api/stores/",
            {"name":"Second store"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
