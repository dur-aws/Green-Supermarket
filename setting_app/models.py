# accounts/models.py
from django.db import models
from django.conf import settings
from django.utils import timezone
import zoneinfo

class ActivityLog(models.Model):
    ACTION_TYPES = [
        ('LOGIN', 'User Login'),
        ('LOGOUT', 'User Logout'),
        ('CREATE', 'Record Created'),
        ('UPDATE', 'Record Updated'),
        ('DELETE', 'Record Deleted'),
        ('DATA_ACCESS', 'Resource/Data Viewed'),
        ('ACCESS_DENIED', 'Access Denied / Permission Error'),
        ('SYSTEM_ERROR', 'System / Server Error'),
    ]

    log_id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activity_logs'
    )
    action_type = models.CharField(max_length=20, choices=ACTION_TYPES, default='VIEW')
    alert_message = models.TextField(blank=True, null=True)
    path = models.CharField(max_length=255)
    method = models.CharField(max_length=10) # GET, POST, PUT, DELETE
    status_code = models.IntegerField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    description = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'activity_log'
        ordering = ['-timestamp']

    # Helper method to get formatted Nepali DateTime string
    @property
    def nepali_timestamp(self):
        kathmandu_tz = zoneinfo.ZoneInfo("Asia/Kathmandu")
        local_dt = self.timestamp.astimezone(kathmandu_tz)
        return local_dt.strftime('%Y-%m-%d %I:%M:%S %p')

    def __str__(self):
        user_str = self.user.username if self.user else "Anonymous"
        return f"[{self.nepali_timestamp}] {user_str} - {self.action_type} ({self.status_code})"