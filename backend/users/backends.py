from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.conf import settings
import supabase

class SupabaseAuthBackend(ModelBackend):
    def authenticate(self, request, token=None, **kwargs):
        User = get_user_model()
        
        if not token:
            return None

        try:
            # Initialize Supabase client
            supabase_client = supabase.create_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_KEY
            )
            
            # Get user from Supabase
            user_data = supabase_client.auth.get_user(token)
            if not user_data.user:
                return None
                
            # Get or create the user
            user, _ = User.objects.get_or_create(
                username=user_data.user.email,
                defaults={
                    'email': user_data.user.email,
                    'supabase_id': user_data.user.id,
                }
            )
            
            # Update user data if needed
            if user.supabase_id != user_data.user.id:
                user.supabase_id = user_data.user.id
                user.save()
                
            return user
            
        except Exception as e:
            print(f"Authentication error: {str(e)}")
            return None

    def get_user(self, user_id):
        User = get_user_model()
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
