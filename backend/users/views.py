from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.conf import settings
from .models import User
from .serializers import UserSerializer
from .backends import SupabaseAuthBackend

# Initialize the auth backend
auth_backend = SupabaseAuthBackend()

# Test view to verify authentication
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def test_auth(request):
    """Test endpoint to verify authentication is working"""
    return Response({
        'message': 'Authentication successful!',
        'user': {
            'id': request.user.id,
            'username': request.user.username,
            'email': request.user.email
        }
    })

@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """Handle user login with Supabase JWT."""
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return Response(
            {'error': 'Bearer token is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    token = auth_header.split(' ')[1]
    if not token:
        return Response(
            {'error': 'Invalid token format'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # Authenticate the user using our backend
        user = auth_backend.authenticate(request, token=token)
        
        if not user:
            return Response(
                {'error': 'Invalid or expired token'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Get or create token for the user
        token, _ = Token.objects.get_or_create(user=user)
        serializer = UserSerializer(user)
        
        return Response({
            'token': token.key,
            'user': serializer.data
        })
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )

@api_view(['POST'])
@permission_classes([AllowAny])
def signup_view(request):
    """Handle user registration with Supabase."""
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return Response(
            {'error': 'Bearer token is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    token = auth_header.split(' ')[1]
    if not token:
        return Response(
            {'error': 'Invalid token format'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # Authenticate the user using our backend
        user = auth_backend.authenticate(request, token=token)
        
        if not user:
            return Response(
                {'error': 'Invalid or expired token'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # If we get here, the user is authenticated
        # Create or get token for the user
        token, _ = Token.objects.get_or_create(user=user)
        serializer = UserSerializer(user)
        
        return Response({
            'message': 'User registered successfully',
            'token': token.key,
            'user': serializer.data
        })
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def verify_token_view(request):
    """Verify if token is valid and return user data."""
    try:
        user = request.user
        serializer = UserSerializer(user)
        return Response({
            'valid': True,
            'user': serializer.data
        })
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_401_UNAUTHORIZED
        )
