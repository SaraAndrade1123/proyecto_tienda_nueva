from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):

    document = models.CharField(max_length=15)
    phone = models.TextField()

