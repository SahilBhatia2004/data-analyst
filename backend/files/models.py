from django.db import models
from django.conf import settings


class UploadedFile(models.Model):
    """Model to track uploaded files and their metadata."""
    FILE_TYPES = [
        ('excel', 'Excel File'),
        ('csv', 'CSV File'),
        ('google_sheet', 'Google Sheet'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='uploaded_files')
    file_name = models.CharField(max_length=255)
    original_name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=20, choices=FILE_TYPES)
    file_size = models.BigIntegerField()
    supabase_path = models.CharField(max_length=500)
    mime_type = models.CharField(max_length=100)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_processed = models.BooleanField(default=False)
    processing_status = models.CharField(max_length=50, default='pending')

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.original_name} ({self.file_type})"


class FileProcessing(models.Model):
    """Model to track file processing status and results."""
    file = models.OneToOneField(UploadedFile, on_delete=models.CASCADE)
    status = models.CharField(max_length=50, default='processing')
    error_message = models.TextField(blank=True, null=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    row_count = models.IntegerField(null=True, blank=True)
    column_count = models.IntegerField(null=True, blank=True)
    data_preview = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f"Processing for {self.file.original_name}"
