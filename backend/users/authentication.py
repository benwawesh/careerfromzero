from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q

User = get_user_model()


class CustomUserBackend(ModelBackend):
    """
    Custom authentication backend that allows login with either username or email.
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None
        
        # Check if input is email or username
        if '@' in username:
            # Login with email
            try:
                user = User.objects.get(email=username)
                if user.check_password(password) and self.user_can_authenticate(user):
                    return user
            except User.DoesNotExist:
                return None
        else:
            # Login with username
            try:
                user = User.objects.get(username=username)
                if user.check_password(password) and self.user_can_authenticate(user):
                    return user
            except User.DoesNotExist:
                return None
        
        return None