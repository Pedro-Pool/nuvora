from django.test import TestCase

from users.models import User

class UserModelTest(TestCase):
    def test_01(self):
        """Test create user with email"""

        user = User.objects.create(
            email="pedro@email.com",
            password="password123",
        )

        self.assertEqual(user.email, "pedro@email.com")
        self.assertTrue(user.is_active)

    def test_02(self):
        """Test email is unique"""

        user = User.objects.create_user(
            email="pedro@email.com",
            password="password123",
        )
        with self.assertRaises(Exception):
            User.objects.create_user(
            email="pedro@email.com",
            password="password-wrong123",
            )