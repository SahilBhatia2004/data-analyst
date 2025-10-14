from django.db import models
from django.conf import settings


class ChatSession(models.Model):
    """Model to store chat sessions."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='chat_sessions')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Chat session {self.id} for {self.user.username}"


class ChatMessage(models.Model):
    """Model to store individual chat messages."""
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE)
    message = models.TextField()
    is_user = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{'User' if self.is_user else 'AI'}: {self.message[:50]}"


class Dashboard(models.Model):
    """Model to store generated dashboards."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='dashboards')
    file_id = models.IntegerField()  # Reference to uploaded file
    query = models.TextField()
    dashboard_data = models.JSONField()
    theme = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Dashboard {self.id} for file {self.file_id}"


class DashboardExport(models.Model):
    """Model to store dashboard exports."""
    EXPORT_FORMATS = [
        ('pdf', 'PDF'),
        ('png', 'PNG Image'),
        ('html', 'HTML'),
    ]

    dashboard = models.ForeignKey(Dashboard, on_delete=models.CASCADE)
    format = models.CharField(max_length=10, choices=EXPORT_FORMATS)
    export_link = models.URLField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Export {self.id} ({self.format}) for dashboard {self.dashboard.id}"
