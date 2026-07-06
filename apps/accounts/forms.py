from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

User = get_user_model()


class UserRegistrationForm(UserCreationForm):
    """
    Registration form based on the custom User model.
    Collects: username, email, role, password, password confirmation.
    password1 and password2 are inherited from UserCreationForm.
    """

    class Meta:
        model = User
        fields = ('username', 'email', 'role')
