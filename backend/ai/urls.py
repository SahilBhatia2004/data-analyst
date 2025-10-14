from django.urls import path
from . import views

urlpatterns = [
    path('chat/', views.chat_view, name='chat'),
    path('dashboard/', views.generate_dashboard_view, name='generate_dashboard'),
    path('dashboard/<int:dashboard_id>/', views.get_dashboard_view, name='get_dashboard'),
    path('dashboard/<int:dashboard_id>/export/', views.export_dashboard_view, name='export_dashboard'),
    path('dashboard/<int:dashboard_id>/save/', views.save_dashboard_to_supabase_view, name='save_dashboard'),
    path('dashboards/list/', views.list_user_dashboards_view, name='list_dashboards'),
    path('dashboards/load/<str:filename>/', views.load_user_dashboard_view, name='load_dashboard'),
]