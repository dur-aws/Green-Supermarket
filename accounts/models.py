from django.db import models
from django.contrib.auth.models import AbstractUser

class Role(models.Model):
    role_id = models.AutoField(primary_key=True)
    role_name = models.CharField(unique=True, max_length=50)

    class Meta:
        db_table = 'role'   # MySQL table name

    def __str__(self):
        return self.role_name


class CustomUser(AbstractUser):
    # Keep the primary key compatible with Django's built-in auth user model.
    id = models.BigAutoField(primary_key=True)
    role = models.ForeignKey(Role, on_delete=models.DO_NOTHING, null=True, blank=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    status = models.IntegerField(default=1)  # 1 = active, 0 = inactive
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'user'   # MySQL table name

    def __str__(self):
        return self.username
