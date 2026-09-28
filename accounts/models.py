from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):

    document = models.CharField(max_length=20, unique=True, null=True, blank=True)
    phone = models.CharField(max_length=20, unique=True, null=True, blank=True)
