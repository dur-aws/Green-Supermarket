from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0002_alter_role_role_name_modulepermission'),
    ]

    operations = [
        migrations.AlterField(
            model_name='modulepermission',
            name='module_name',
            field=models.CharField(
                choices=[
                    ('dashboard', 'Dashboard'),
                    ('accounts', 'User & Accounts Management'),
                    ('categories', 'Categories'),
                    ('products', 'Products'),
                    ('suppliers', 'Suppliers'),
                    ('customers', 'Customers'),
                    ('sales', 'Sales'),
                    ('inventory', 'Inventory'),
                    ('accounting', 'Accounting'),
                ],
                max_length=50,
            ),
        ),
    ]
