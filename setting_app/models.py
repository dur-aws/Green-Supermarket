
from datetime import datetime
from django.db import models
from django.conf import settings
from zoneinfo import ZoneInfo
import nepali_datetime

KATHMANDU_TZ = ZoneInfo("Asia/Kathmandu")


def kathmandu_now():
    return datetime.now(KATHMANDU_TZ).replace(tzinfo=None)


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
    timestamp = models.DateTimeField(default=kathmandu_now)
    nepali_time = models.CharField(max_length=19, blank=True, editable=False)

    class Meta:
        db_table = 'activity_log'
        ordering = ['-timestamp']

    def save(self, *args, **kwargs):
        local_dt = self.timestamp.replace(tzinfo=KATHMANDU_TZ)
        nepali_dt = nepali_datetime.datetime.from_datetime_datetime(local_dt)
        self.nepali_time = nepali_dt.strftime("%Y-%m-%d %H:%M:%S")
        super().save(*args, **kwargs)

    @property
    def nepali_timestamp(self):
        return self.nepali_time

    @property
    def kathmandu_timestamp(self):
        return self.timestamp.strftime("%Y-%m-%d %H:%M:%S")
