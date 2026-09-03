from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager


class Role(models.Model):
    # Constants matching database ENUM string values exactly
    ADMIN = 'ADMIN'
    MANAGER = 'MANAGER'
    STAFF = 'STAFF'
    SUPPLIER = 'SUPPLIER'

    ROLE_CHOICES = [
        (ADMIN, 'admin'),
        (MANAGER, 'manager'),
        (STAFF, 'staff'),
        (SUPPLIER, 'supplier'),
    ]

    role_id = models.AutoField(primary_key=True)
    role_name = models.CharField(
        max_length=50,
        unique=True,
        choices=ROLE_CHOICES
    )

    class Meta:
        db_table = 'role'

    def __str__(self):
        return self.role_name

class CustomUserManager(BaseUserManager):
    def create_user(self, username, email=None, password=None, role_name=None, **extra_fields):
        if not username:
            raise ValueError("The Username must be set")
        if not email:
            raise ValueError("The Email must be set")

        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)

        if role_name:
            user.role = role_name   # assuming role_name is a Role instance (FK)
        
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        # force ADMIN role - all superusers to be ADMIN
        admin_role = Role.objects.get(role_name="ADMIN")
        return self.create_user(username, email, password=password, role_name=admin_role, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    id = models.BigAutoField(primary_key=True)
    username = models.CharField(max_length=150, unique=True)
    password = models.CharField(max_length=128)  # handled securely by AbstractBaseUser
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    email = models.EmailField(max_length=254)
    phone = models.CharField(max_length=20, blank=True, null=True)
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True)

    status = models.SmallIntegerField(default=1)  # 1 = Active, 0 = Inactive
    is_superuser = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    last_login = models.DateTimeField(blank=True, null=True)
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = CustomUserManager()

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email", "role"]

    class Meta:
        db_table = "user"

    def __str__(self):
        return self.username


    # Helper properties for ENUM checks
    @property
    def is_admin_role(self):
        return self.role and self.role.role_name == Role.ADMIN

    @property
    def is_manager_role(self):
        return self.role and self.role.role_name == Role.MANAGER

    @property
    def is_staff_role(self):
        return self.role and self.role.role_name == Role.STAFF

    @property
    def is_supplier_role(self):
        return self.role and self.role.role_name == Role.SUPPLIER
class ModulePermission(models.Model):
    MODULE_CHOICES = [
        ('dashboard', 'Dashboard'),
        ('accounts', 'User & Accounts Management'),
        ('categories', 'Categories'),
        ('products', 'Products'),
        ('suppliers', 'Suppliers'),
        ('customers', 'Customers'),
        ('sales', 'Sales'),
        ('inventory', 'Inventory'),
    ]

    role = models.ForeignKey(Role,  on_delete=models.SET_NULL, null=True, related_name='permissions')
    module_name = models.CharField(max_length=50, choices=MODULE_CHOICES)
    can_view = models.BooleanField(default=False)
    can_add = models.BooleanField(default=False)
    can_edit = models.BooleanField(default=False)
    can_delete = models.BooleanField(default=False)

    class Meta:
        unique_together = ('role', 'module_name')

    def __str__(self):
        return f"{self.role.role_name} - {self.module_name}"