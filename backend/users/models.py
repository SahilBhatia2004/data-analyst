from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.contrib.auth import get_user_model

class User(AbstractUser):
    """Extended user model for the AI Data Analyst platform."""
    supabase_id = models.CharField(max_length=255, blank=True, null=True, unique=True)
    avatar_url = models.URLField(blank=True, null=True)
    preferences = models.JSONField(default=dict, blank=True)

    class Meta:
        # Add this to avoid permission conflicts
        swappable = 'AUTH_USER_MODEL'

    def __str__(self):
        return self.username
        
    @property
    def is_authenticated(self):
        """
        Always return True. This is a way to tell if the user has been
        authenticated in templates.
        """
        return True

    @property
    def is_anonymous(self):
        """
        Always return False. This is a way of comparing User objects to
        anonymous users.
        """
        return False

    def get_auth_token(self):
        """
        Get or create an auth token for the user.
        """
        from rest_framework.authtoken.models import Token
        token, created = Token.objects.get_or_create(user=self)
        return token.key
