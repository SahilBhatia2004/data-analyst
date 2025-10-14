from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
import jwt
import requests
from jwt.algorithms import RSAAlgorithm
from jwt import PyJWKClient

User = get_user_model()

class SupabaseAuthentication(BaseAuthentication):
    """
    Supabase JWT authentication backend.
    Validates the JWT token from Supabase and returns the authenticated user.
    """
    def __init__(self):
        self.jwks_client = PyJWKClient(f"https://{settings.SUPABASE_PROJECT_ID}.supabase.co/auth/v1/jwks")
        self.issuer = f"https://{settings.SUPABASE_PROJECT_ID}.supabase.co/auth/v1"
        self.audience = "authenticated"

    def authenticate(self, request):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return None

        token = auth_header.split(' ')[1]
        
        try:
            # Get the signing key from JWKS endpoint
            signing_key = self.jwks_client.get_signing_key_from_jwt(token)
            
            # Decode and verify the token
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=self.audience,
                issuer=self.issuer,
                options={"verify_aud": True, "verify_iss": True}
            )
            
            # Get or create the user
            user, _ = User.objects.get_or_create(
                username=payload['email'],
                defaults={
                    'email': payload['email'],
                    'first_name': payload.get('user_metadata', {}).get('first_name', ''),
                    'last_name': payload.get('user_metadata', {}).get('last_name', ''),
                    'is_active': True
                }
            )
            
            return (user, None)
            
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed('Token has expired')
        except jwt.InvalidTokenError as e:
            raise AuthenticationFailed(f'Invalid token: {str(e)}')
        except Exception as e:
            raise AuthenticationFailed(f'Authentication failed: {str(e)}')

    def authenticate_header(self, request):
        return 'Bearer realm="api"'

def get_user_from_token(token):
    """Helper function to get user from Supabase JWT token"""
    auth = SupabaseAuthentication()
    return auth.authenticate_credentials(token)
