from django.db import models
from django.conf import settings
from django.utils import timezone

class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('danger', 'Danger / Critical'),
        ('warning', 'Warning'),
        ('info', 'Information'),
        ('success', 'Success'),
    )
    user = models.ForeignKey(
            settings.AUTH_USER_MODEL, 
            on_delete=models.SET_NULL, 
            null=True, 
            blank=True,
            related_name='notifications'
        )
    title = models.CharField(max_length=150)
    message = models.TextField()
    type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, default='info')
    link = models.CharField(max_length=255, blank=True, null=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"

    def time_ago(self):
        now = timezone.now()
        diff = now - self.created_at
        
        if diff.days > 0:
            return f"{diff.days}d ago"
        seconds = diff.seconds
        if seconds < 60:
            return "Just now"
        if seconds < 3600:
            return f"{seconds // 60}m ago"
        return f"{seconds // 3600}h ago"