from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

User = get_user_model()


class UserRegistrationForm(UserCreationForm):
    """
    Registration form.
    Every new user is registered as USER.
    """

    class Meta:
        model = User
        fields = (
            "username",
            "email",
        )

    def save(self, commit=True):
        user = super().save(commit=False)

        user.role = User.Role.USER

        if commit:
            user.save()

        return user