from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from .managers import UserManager

class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(max_length=150, unique=True)

    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    def __str__(self):
        return self.email
