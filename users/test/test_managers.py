from django.test import TestCase

from users.models import User

class UserManagerTests(TestCase):

    def test_01(self):
        """Test create user"""

        user = User.objects.create_user(
            email="pedro@email.com",
            password="password123",
            )

        self.assertEqual(user.email, "pedro@email.com")
        self.assertTrue(user.check_password("password123"))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.is_active)

    def test_02(self):
        """Test create user with wrong password"""

        user = User.objects.create_user(
            email="pedro@email.com",
            password="password123",
        )
        self.assertFalse(user.check_password("password-wrong"))

    def test_03(self):
        """Test create superuser"""

        user = User.objects.create_superuser(
            email="admin@email.com",
            password="password123",
        )
        self.assertEqual(user.email, "admin@email.com")
        self.assertTrue(user.check_password("password123"))
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_active)