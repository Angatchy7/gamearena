# pyrefly: ignore [missing-import]
from apps.accounts.models import User

ADMIN = User.Role.ADMIN
MANAGER = User.Role.MANAGER
PLAYER = User.Role.PLAYER