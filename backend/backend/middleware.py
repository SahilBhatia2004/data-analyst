from django.contrib.auth.middleware import AuthenticationMiddleware
from django.contrib.auth import get_user_model

class SupabaseAuthMiddleware(AuthenticationMiddleware):
    def process_request(self, request):
        # Skip authentication for these paths
        if request.path.startswith('/admin/') or request.path.startswith('/api/auth/'):
            return None

        # Get the token from the Authorization header
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if not auth_header.startswith('Bearer '):
            return None

        token = auth_header.split(' ')[1]
        if not token:
            return None

        # Authenticate the user
        user = self.authenticate(request, token)
        if user:
            request.user = user
            request._dont_enforce_csrf_checks = True

    def authenticate(self, request, token):
        from django.contrib.auth import authenticate
        return authenticate(request, token=token)
