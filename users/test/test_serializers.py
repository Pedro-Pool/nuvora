from django.contrib.auth.base_user import AbstractBaseUser
from django.test import TestCase

from users.models import User
from users.serializers import RegisterSerializer

class RegisterSerializerTest(TestCase):
    def test_01(self):
        """Test create serializer"""

        data = {
            "email": "pedro@email.com",
            "first_name": "pedro",
            "last_name": "silva",
            "password": "password123",
        }

        serializer = RegisterSerializer(data=data)
        self.assertTrue(serializer.is_valid())

        user = serializer.save()

        self.assertEqual(user.email, "pedro@email.com")
        self.assertTrue(user.check_password("password123"))
        self.assertNotEqual(user.password, "password123")

    def test_02(self):
        """Test password must have at least 8 characters"""

        data = {
            "email": "pedro@email.com",
            "password": "123",
        }
        serializer = RegisterSerializer(data=data)

        self.assertFalse(serializer.is_valid())
        self.assertIn("password", serializer.errors)