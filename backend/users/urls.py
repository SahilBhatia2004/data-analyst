from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('verify-token/', views.verify_token_view, name='verify_token'),
    path('test-auth/', views.test_auth, name='test_auth'),
]
