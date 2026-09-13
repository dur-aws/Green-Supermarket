# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class Account(models.Model):
    account_id = models.AutoField(primary_key=True)
    account_code = models.CharField(unique=True, max_length=20)
    account_name = models.CharField(max_length=100)
    account_type = models.CharField(max_length=10)
    is_active = models.IntegerField()
    parent_account = models.ForeignKey('self', models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'account'


class AccountsModulepermission(models.Model):
    id = models.BigAutoField(primary_key=True)
    module_name = models.CharField(max_length=50)
    can_view = models.IntegerField()
    can_add = models.IntegerField()
    can_edit = models.IntegerField()
    can_delete = models.IntegerField()
    role = models.ForeignKey('Role', models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'accounts_modulepermission'
        unique_together = (('role', 'module_name'),)


class ActivityLog(models.Model):
    log_id = models.BigAutoField(primary_key=True)
    action_type = models.CharField(max_length=20)
    path = models.CharField(max_length=255)
    method = models.CharField(max_length=10)
    status_code = models.IntegerField(blank=True, null=True)
    ip_address = models.CharField(max_length=39, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField()
    user = models.ForeignKey('User', models.DO_NOTHING, blank=True, null=True)
    alert_message = models.TextField(blank=True, null=True)
    nepali_time = models.CharField(max_length=19)

    class Meta:
        managed = False
        db_table = 'activity_log'


class AuthGroup(models.Model):
    name = models.CharField(unique=True, max_length=150)

    class Meta:
        managed = False
        db_table = 'auth_group'


class AuthGroupPermissions(models.Model):
    id = models.BigAutoField(primary_key=True)
    group = models.ForeignKey(AuthGroup, models.DO_NOTHING)
    permission = models.ForeignKey('AuthPermission', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_group_permissions'
        unique_together = (('group', 'permission'),)


class AuthPermission(models.Model):
    name = models.CharField(max_length=255)
    content_type = models.ForeignKey('DjangoContentType', models.DO_NOTHING)
    codename = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'auth_permission'
        unique_together = (('content_type', 'codename'),)


class Category(models.Model):
    category_id = models.AutoField(primary_key=True)
    parent = models.ForeignKey('self', models.DB_CASCADE, blank=True, null=True)
    category_name = models.CharField(max_length=100)
    requires_expiry_tracking = models.IntegerField(blank=True, null=True)
    requires_batch_tracking = models.IntegerField(blank=True, null=True)
    requires_catch_weight = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'category'


class CompanyProfile(models.Model):
    company_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    trade_name = models.CharField(max_length=255, blank=True, null=True)
    pan_number = models.CharField(unique=True, max_length=20)
    address = models.TextField()
    phone = models.CharField(max_length=20)
    is_vat_registered = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'company_profile'


class Customer(models.Model):
    customer_id = models.AutoField(primary_key=True)
    customer_code = models.CharField(unique=True, max_length=20)
    customer_name = models.CharField(max_length=100)
    phone = models.CharField(unique=True, max_length=20, blank=True, null=True)
    email = models.CharField(unique=True, max_length=100, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=8, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    account = models.ForeignKey(Account, models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'customer'


class DashboardNotification(models.Model):
    id = models.BigAutoField(primary_key=True)
    title = models.CharField(max_length=150)
    message = models.TextField()
    type = models.CharField(max_length=20)
    link = models.CharField(max_length=255, blank=True, null=True)
    is_read = models.IntegerField()
    created_at = models.DateTimeField()
    user = models.ForeignKey('User', models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'dashboard_notification'


class DjangoAdminLog(models.Model):
    action_time = models.DateTimeField()
    object_id = models.TextField(blank=True, null=True)
    object_repr = models.CharField(max_length=200)
    action_flag = models.PositiveSmallIntegerField()
    change_message = models.TextField()
    content_type = models.ForeignKey('DjangoContentType', models.DO_NOTHING, blank=True, null=True)
    user = models.ForeignKey('User', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'django_admin_log'


class DjangoContentType(models.Model):
    app_label = models.CharField(max_length=100)
    model = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'django_content_type'
        unique_together = (('app_label', 'model'),)


class DjangoMigrations(models.Model):
    id = models.BigAutoField(primary_key=True)
    app = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    applied = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'django_migrations'


class DjangoSession(models.Model):
    session_key = models.CharField(primary_key=True, max_length=40)
    session_data = models.TextField()
    expire_date = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'django_session'


class DynamicPriceMarkdown(models.Model):
    markdown_id = models.AutoField(primary_key=True)
    batch = models.ForeignKey('InventoryBatch', models.DB_CASCADE)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    original_price = models.DecimalField(max_digits=10, decimal_places=2)
    discounted_price = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.IntegerField(blank=True, null=True)
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'dynamic_price_markdown'


class FiscalYear(models.Model):
    name = models.CharField(unique=True, max_length=20)
    start_date = models.DateField()
    end_date = models.DateField()
    is_closed = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'fiscal_year'


class InventoryBatch(models.Model):
    batch_id = models.AutoField(primary_key=True)
    variant = models.ForeignKey('ProductVariant', models.DO_NOTHING)
    supplier = models.ForeignKey('Supplier', models.DB_SET_NULL, blank=True, null=True)
    purchase_detail = models.ForeignKey('PurchaseDetail', models.DB_SET_NULL, blank=True, null=True)
    batch_number = models.CharField(max_length=50)
    manufacture_date = models.DateField(blank=True, null=True)
    harvest_date = models.DateField(blank=True, null=True)
    expiry_date = models.DateField()
    received_date = models.DateField()
    received_quantity = models.DecimalField(max_digits=10, decimal_places=3)
    current_quantity = models.DecimalField(max_digits=10, decimal_places=3)
    unit_cost_price = models.DecimalField(max_digits=10, decimal_places=2)
    batch_status = models.CharField(max_length=11, blank=True, null=True)
    journal_entry = models.ForeignKey('JournalEntry', models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'inventory_batch'


class JournalEntry(models.Model):
    entry_id = models.AutoField(primary_key=True)
    entry_date = models.DateField()
    description = models.CharField(max_length=255)
    reference_type = models.CharField(max_length=10)
    reference_id = models.IntegerField(blank=True, null=True)
    fiscal_year = models.CharField(max_length=20)
    created_at = models.DateTimeField()
    created_by = models.ForeignKey('User', models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'journal_entry'


class JournalItem(models.Model):
    item_id = models.AutoField(primary_key=True)
    debit = models.DecimalField(max_digits=12, decimal_places=2)
    credit = models.DecimalField(max_digits=12, decimal_places=2)
    account = models.ForeignKey(Account, models.DO_NOTHING)
    entry = models.ForeignKey(JournalEntry, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'journal_item'


class Membership(models.Model):
    membership_id = models.AutoField(primary_key=True)
    membership_type = models.CharField(max_length=50)
    start_date = models.DateField()
    expiry_date = models.DateField()
    membership_fee = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=9, blank=True, null=True)
    customer = models.ForeignKey(Customer, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'membership'


class PaymentReceipt(models.Model):
    voucher_no = models.CharField(unique=True, max_length=50)
    party_type = models.CharField(max_length=10)
    payment_mode = models.CharField(max_length=20)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_date = models.DateField()
    reference_number = models.CharField(max_length=100, blank=True, null=True)
    narration = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField()
    customer = models.ForeignKey(Customer, models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'payment_receipt'


class Product(models.Model):
    product_id = models.AutoField(primary_key=True)
    category = models.ForeignKey(Category, models.DO_NOTHING)
    brand = models.CharField(max_length=100, blank=True, null=True)
    product_name = models.CharField(max_length=150)
    is_organic = models.IntegerField(blank=True, null=True)
    is_eco_friendly = models.IntegerField(blank=True, null=True)
    shelf_life_days = models.IntegerField(blank=True, null=True)
    status = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'product'


class ProductVariant(models.Model):
    variant_id = models.AutoField(primary_key=True)
    product = models.ForeignKey(Product, models.DB_CASCADE)
    sku = models.CharField(unique=True, max_length=50)
    barcode = models.CharField(unique=True, max_length=100, blank=True, null=True)
    variant_name = models.CharField(max_length=150)
    primary_uom = models.ForeignKey('UnitOfMeasure', models.DO_NOTHING)
    secondary_uom = models.ForeignKey('UnitOfMeasure', models.DB_SET_NULL, related_name='productvariant_secondary_uom_set', blank=True, null=True)
    is_catch_weight = models.IntegerField(blank=True, null=True)
    cost_price = models.DecimalField(max_digits=12, decimal_places=2)
    selling_price = models.DecimalField(max_digits=12, decimal_places=2)
    is_vatable = models.IntegerField()
    reorder_level = models.DecimalField(max_digits=10, decimal_places=3)
    target_stock_level = models.DecimalField(max_digits=10, decimal_places=3)
    abc_class = models.CharField(max_length=1, blank=True, null=True)
    is_active = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'product_variant'


class PurchaseDetail(models.Model):
    purchase_detail_id = models.AutoField(primary_key=True)
    purchase = models.ForeignKey('PurchaseOrder', models.DB_CASCADE)
    variant = models.ForeignKey(ProductVariant, models.DO_NOTHING, blank=True, null=True)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    manufacture_date = models.DateField(blank=True, null=True)
    harvest_date = models.DateField(blank=True, null=True)
    expiry_date = models.DateField(blank=True, null=True)
    ordered_quantity = models.DecimalField(max_digits=10, decimal_places=3, db_comment='Qty requested')
    agreed_unit_price = models.DecimalField(max_digits=10, decimal_places=2, db_comment='Initial PO price')
    received_quantity = models.DecimalField(max_digits=10, decimal_places=3, blank=True, null=True, db_comment='Actual catch-weight received')
    actual_unit_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, db_comment='Price charged on final supplier invoice')

    class Meta:
        managed = False
        db_table = 'purchase_detail'


class PurchaseOrder(models.Model):
    purchase_id = models.AutoField(primary_key=True)
    supplier = models.ForeignKey('Supplier', models.DO_NOTHING)
    received_by_user = models.ForeignKey('User', models.DO_NOTHING)
    invoice_number = models.CharField(max_length=50, blank=True, null=True)
    order_date = models.DateField(blank=True, null=True)
    received_date = models.DateField(blank=True, null=True)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    vat_amount = models.DecimalField(max_digits=12, decimal_places=2)
    tds_rate = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    tds_amount = models.DecimalField(max_digits=12, decimal_places=2)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    net_payable_amount = models.DecimalField(max_digits=12, decimal_places=2)
    order_status = models.CharField(max_length=9)
    payment_status = models.CharField(max_length=7)
    delivery_date = models.DateField(blank=True, null=True)
    journal_entry = models.ForeignKey(JournalEntry, models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'purchase_order'


class Role(models.Model):
    role_id = models.AutoField(primary_key=True)
    role_name = models.CharField(unique=True, max_length=30)

    class Meta:
        managed = False
        db_table = 'role'


class Sale(models.Model):
    sales_id = models.AutoField(primary_key=True)
    invoice_no = models.IntegerField(unique=True)
    sale_date = models.DateTimeField()
    bs_date = models.CharField(max_length=15, blank=True, null=True)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    discount_total = models.DecimalField(max_digits=12, decimal_places=2)
    non_taxable_amount = models.DecimalField(max_digits=12, decimal_places=2)
    taxable_amount = models.DecimalField(max_digits=12, decimal_places=2)
    vat_total = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    round_off = models.DecimalField(max_digits=6, decimal_places=2)
    grand_total = models.DecimalField(max_digits=12, decimal_places=2)
    tender_amount = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    received_amount = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    change_amount = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    payment_status = models.CharField(max_length=14)
    payment_mode = models.CharField(max_length=10)
    narration = models.TextField(blank=True, null=True)
    idempotency_key = models.CharField(unique=True, max_length=64, blank=True, null=True)
    user_id = models.BigIntegerField(blank=True, null=True)
    sales_ac_id = models.CharField(max_length=50)
    buyer_name = models.CharField(max_length=100, blank=True, null=True)
    customer_id = models.IntegerField(blank=True, null=True)
    customer_pan = models.CharField(max_length=20, blank=True, null=True)
    sale_status = models.CharField(max_length=20)
    fiscal_year = models.ForeignKey(FiscalYear, models.DO_NOTHING, blank=True, null=True)
    journal_entry = models.ForeignKey(JournalEntry, models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'sale'


class SaleItem(models.Model):
    sale_item_id = models.AutoField(primary_key=True)
    quantity = models.DecimalField(max_digits=10, decimal_places=3)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2)
    vat_percent = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    net_subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    batch = models.ForeignKey(InventoryBatch, models.DO_NOTHING, blank=True, null=True)
    sale = models.ForeignKey(Sale, models.DO_NOTHING)
    variant = models.ForeignKey(ProductVariant, models.DO_NOTHING)
    discount_percent = models.DecimalField(max_digits=10, decimal_places=2)
    vat_amount = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    line_total = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        managed = False
        db_table = 'sale_item'


class StockAdjustment(models.Model):
    adjustment_id = models.AutoField(primary_key=True)
    batch = models.ForeignKey(InventoryBatch, models.DO_NOTHING)
    adjusted_by_user = models.ForeignKey('User', models.DO_NOTHING)
    quantity_change = models.DecimalField(max_digits=10, decimal_places=3, db_comment='Negative for loss, positive for correction')
    reason_code = models.CharField(max_length=16)
    loss_value = models.DecimalField(max_digits=10, decimal_places=2)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'stock_adjustment'


class Supplier(models.Model):
    supplier_id = models.AutoField(primary_key=True)
    supplier_name = models.CharField(max_length=150)
    contact_person = models.CharField(max_length=100, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.CharField(unique=True, max_length=254, blank=True, null=True)
    pan_vat_number = models.CharField(max_length=20, blank=True, null=True)
    is_organic_certified = models.IntegerField(blank=True, null=True)
    certification_details = models.CharField(max_length=255, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    is_active = models.IntegerField(blank=True, null=True)
    user = models.ForeignKey(AuthPermission, models.DO_NOTHING, blank=True, null=True)
    account = models.ForeignKey(Account, models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'supplier'


class UnitOfMeasure(models.Model):
    uom_id = models.AutoField(primary_key=True)
    unit_name = models.CharField(unique=True, max_length=50)
    notation = models.CharField(max_length=10)
    is_weight_based = models.IntegerField(blank=True, null=True)
    is_active = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'unit_of_measure'


class User(models.Model):
    id = models.BigAutoField(primary_key=True)
    username = models.CharField(unique=True, max_length=150)
    password = models.CharField(max_length=128)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    email = models.CharField(max_length=254)
    phone = models.CharField(max_length=20, blank=True, null=True)
    status = models.SmallIntegerField()
    is_superuser = models.IntegerField()
    is_staff = models.IntegerField()
    is_active = models.IntegerField()
    last_login = models.DateTimeField(blank=True, null=True)
    date_joined = models.DateTimeField()
    role = models.ForeignKey(Role, models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'user'


class UserGroups(models.Model):
    id = models.BigAutoField(primary_key=True)
    customuser = models.ForeignKey(User, models.DO_NOTHING)
    group = models.ForeignKey(AuthGroup, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'user_groups'
        unique_together = (('customuser', 'group'),)


class UserUserPermissions(models.Model):
    id = models.BigAutoField(primary_key=True)
    customuser = models.ForeignKey(User, models.DO_NOTHING)
    permission = models.ForeignKey(AuthPermission, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'user_user_permissions'
        unique_together = (('customuser', 'permission'),)
