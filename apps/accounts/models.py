from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom User model extending AbstractUser.
    All default fields (username, email, first_name, last_name,
    password, is_staff, is_active, date_joined, etc.) are inherited
    unchanged from AbstractUser.
    """

    class Role(models.TextChoices):
        ADMIN   = 'ADMIN',   'Admin'
        CAPTAIN = 'CAPTAIN', 'Captain'
        PLAYER  = 'PLAYER',  'Player'

    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.PLAYER,
    )

    def __str__(self):
        return f'{self.username} ({self.get_role_display()})'
