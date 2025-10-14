from django.contrib.auth import get_user_model
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import AnonymousUser
import supabase
from django.conf import settings
from rest_framework.authtoken.models import Token

class SupabaseBackend(BaseBackend):
    def authenticate(self, request, token=None, **kwargs):
        if not token:
            return None
            
        User = get_user_model()
        
        try:
            # Initialize Supabase client
            supabase_client = supabase.create_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_KEY
            )
            
            # Get user from Supabase using the token
            user_data = supabase_client.auth.get_user(token)
            if not user_data.user:
                return None
                
            # Get or create the user in your database
            user, created = User.objects.get_or_create(
                username=user_data.user.email,
                defaults={
                    'email': user_data.user.email,
                    'supabase_id': user_data.user.id,
                }
            )
            
            # Update user data if not created
            if not created:
                user.supabase_id = user_data.user.id
                user.save()
            
            # Add is_authenticated attribute
            user.is_authenticated = True
            
            # Create or get token for the user
            token, _ = Token.objects.get_or_create(user=user)
            
            return user
            
        except Exception as e:
            print(f"Authentication error: {str(e)}")
            return None
    
    def get_user(self, user_id):
        User = get_user_model()
        try:
            user = User.objects.get(pk=user_id)
            user.is_authenticated = True
            return user
        except User.DoesNotExist:
            return AnonymousUser()

class SupabaseAuthentication:
    def __init__(self, get_response):
        self.get_response = get_response
        self.backend = SupabaseBackend()

    def __call__(self, request):
        # Skip for non-API endpoints
        if not request.path.startswith('/api/'):
            return self.get_response(request)
            
        # Get the token from the Authorization header
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            request.user = AnonymousUser()
            return self.get_response(request)
            
        token = auth_header.split(' ')[1]
        if not token:
            request.user = AnonymousUser()
            return self.get_response(request)
            
        # Authenticate the user
        user = self.backend.authenticate(request, token=token)
        if user:
            request.user = user
            request.user.is_authenticated = True
        else:
            request.user = AnonymousUser()
            
        return self.get_response(request)
