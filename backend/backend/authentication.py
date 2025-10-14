from rest_framework import authentication, exceptions
from supabase import create_client, Client as SupabaseClient
import os
from django.conf import settings

class SupabaseJWTAuthentication(authentication.BaseAuthentication):
    """
    Custom authentication class for Supabase JWT authentication.
    """
    
    def __init__(self):
        self.supabase: SupabaseClient = create_client(
            os.getenv('SUPABASE_URL'),
            os.getenv('SUPABASE_KEY')
        )
    
    def authenticate(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        
        if not auth_header:
            return None
            
        try:
            # Extract the token from the header (format: 'Bearer <token>')
            token = auth_header.split(' ')[1] if ' ' in auth_header else auth_header
            
            # Verify the token with Supabase
            user = self.supabase.auth.get_user(token)
            
            if not user or not user.user:
                raise exceptions.AuthenticationFailed('Invalid authentication token')
                
            # You can return a Django user here if you have a custom user model
            # For now, we'll return a tuple of (user, None) where user is the Supabase user
            return (user.user, None)
            
        except Exception as e:
            raise exceptions.AuthenticationFailed(f'Authentication failed: {str(e)}')
    
    def authenticate_header(self, request):
        return 'Bearer realm="api"'
