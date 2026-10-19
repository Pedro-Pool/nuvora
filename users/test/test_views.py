from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.serializers import RefreshToken

from users.models import User

class RegisterViewTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.url = "/api/auth/register/"

    def test_01(self):
        """Test register user successfully"""

        data = {
            "email": "pedro@email.com",
            "first_name": "pedro",
            "last_name": "Silva",
            "password": "password123",
        }
        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(email="pedro@email.com").exists())

        user = User.objects.get(email="pedro@email.com")

        self.assertTrue(user.check_password("password123"))
        self.assertNotEqual(user.password, "password123")

    def test_02(self):
        """Test register user wit invalid email"""

        data = {
            "email": "email-invalid",
            "first_name": "pedro",
            "last_name": "Silva",
            "password": "password123",
        }

        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(email="email-invalid").exists())

    def test_03(self):
        """Test register user with short password"""

        data = {
            "email": "pedro@email.com",
            "first_name": "pedro",
            "last_name": "Silva",
            "password": "123",
        }

        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(email="pedro@email.com").exists())

class LoginViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = "/api/auth/login/"

        User.objects.create_user(
            email="pedro@email.com",
            first_name="pedro",
            last_name="Silva",
            password="password123",
        )
    def test_01(self):
        """Test login return tokens"""

        response = self.client.post(
            self.url, {
                "email": "pedro@email.com",
                "first_name": "pedro",
                "last_name": "Silva",
                "password": "password123",
            }, format="json"
        )

        response_data = response.json()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response_data)
        self.assertIn("refresh", response_data)

    def test_02(self):
        """Test login with wrong password"""

        response = self.client.post(
            self.url, {
                "email": "pedro@email.com",
                "password": "password_wrong",
            }, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

class RefreshTokenViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = "/api/auth/refresh/"
        user = User.objects.create_user(
            email="pedro@email.com",
            first_name="Pedro",
            last_name="Silva",
            password="password123",
        )

        self.refresh_token = str(RefreshToken.for_user(user))

    def test_01(self):
        """Test refresh token successfully"""

        response = self.client.post(
            self.url,
            {"refresh": self.refresh_token},
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.json())

    def test_02(self):
        """Test refresh token invalid"""

        response = self.client.post(
            self.url,
            {"refresh": "invalid token"},
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

class MeViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.user = User.objects.create_user(
            email="pedro@email.com",
            first_name="Pedro",
            last_name="Silva",
            password="password123",
        )

        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)

        self.url = "/api/users/me/"

    def test_01(self):
        """Test authenticated user can access"""

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.access_token}"
        )
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "pedro@email.com")
        self.assertEqual(response.data["first_name"], "Pedro")
        self.assertEqual(response.data["last_name"], "Silva")

    def test_02(self):
        """Test unauthenticated user cannot access me"""

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)