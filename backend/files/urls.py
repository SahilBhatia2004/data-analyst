from django.urls import path
from . import views

urlpatterns = [
    path('upload/', views.upload_file, name='upload_file'),
    path('google-sheet/', views.connect_google_sheet, name='connect_google_sheet'),
    path('list/', views.list_files, name='list_files'),
    path('preview/<int:file_id>/', views.get_file_preview, name='get_file_preview'),
    path('delete/<int:file_id>/', views.delete_file, name='delete_file'),
]
