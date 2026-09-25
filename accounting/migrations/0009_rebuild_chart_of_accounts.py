from django.db import migrations


ACCOUNT_DEFINITIONS = [
    ('1000', 'ASSETS', 'ASSET', None),
    ('1100', 'Cash & Bank', 'ASSET', '1000'),
    ('1110', 'Cash in Hand', 'ASSET', '1100'),
    ('1120', 'Bank Account', 'ASSET', '1100'),
    ('1130', 'Fonepay / Digital Wallet', 'ASSET', '1100'),
    ('1200', 'Receivables', 'ASSET', '1000'),
    ('1210', 'Accounts Receivable', 'ASSET', '1200'),
    ('1220', 'Refund Clearing', 'ASSET', '1200'),
    ('1300', 'Inventory', 'ASSET', '1000'),
    ('1310', 'Inventory Asset', 'ASSET', '1300'),
    ('2000', 'LIABILITIES', 'LIABILITY', None),
    ('2100', 'Accounts Payable', 'LIABILITY', '2000'),
    ('2200', 'VAT Payable', 'LIABILITY', '2000'),
    ('2300', 'TDS Payable', 'LIABILITY', '2000'),
    ('3000', 'EQUITY', 'EQUITY', None),
    ('3100', "Owner's Capital", 'EQUITY', '3000'),
    ('3200', 'Retained Earnings', 'EQUITY', '3000'),
    ('4000', 'REVENUE', 'REVENUE', None),
    ('4100', 'Sales Revenue', 'REVENUE', '4000'),
    ('5000', 'COST OF SALES', 'EXPENSE', None),
    ('5100', 'Cost of Goods Sold', 'EXPENSE', '5000'),
    ('6000', 'EXPENSES', 'EXPENSE', None),
    ('6010', 'Rent Expense', 'EXPENSE', '6000'),
    ('6020', 'Salary Expense', 'EXPENSE', '6000'),
    ('6030', 'Electricity Expense', 'EXPENSE', '6000'),
    ('6040', 'Internet Expense', 'EXPENSE', '6000'),
    ('6050', 'Packaging Expense', 'EXPENSE', '6000'),
    ('6060', 'Delivery Expense', 'EXPENSE', '6000'),
    ('6070', 'Bank Charges', 'EXPENSE', '6000'),
    ('6080', 'Marketing Expense', 'EXPENSE', '6000'),
    ('6090', 'Depreciation Expense', 'EXPENSE', '6000'),
    ('6100', 'Inventory Wastage / Loss', 'EXPENSE', '6000'),
    ('6200', 'Sales Discounts', 'EXPENSE', '6000'),
    ('6300', 'Round-off Loss', 'EXPENSE', '6000'),
    ('7000', 'OTHER INCOME', 'REVENUE', None),
    ('7100', 'Round-off Gain', 'REVENUE', '7000'),
]

LEGACY_CODE_MAP = {
    '1010': '1110', '1020': '1120', '1030': '1130',
    '1100': '1210', '1110': '1220', '1200': '1310',
    '1210': '2100', '2010': '2100', '2020': '2200',
    '2030': '2200', '2040': '2300', '3010': '4100',
    '3020': '6200', '3030': '6300', '4010': '5100',
    '4020': '6100',
}


def rebuild_chart(apps, schema_editor):
    Account = apps.get_model('accounting', 'Account')
    JournalItem = apps.get_model('accounting', 'JournalItem')

    legacy_rows = {}
    for old_code in LEGACY_CODE_MAP:
        row = Account.objects.filter(account_code=old_code).first()
        if row:
            legacy_rows[old_code] = row
            row.account_code = f'__old_{row.pk}'
            row.save(update_fields=['account_code'])

    for old_code, new_code in LEGACY_CODE_MAP.items():
        row = legacy_rows.get(old_code)
        if not row:
            continue
        target = Account.objects.filter(account_code=new_code).first()
        if target and target.pk != row.pk:
            JournalItem.objects.filter(account_id=row.pk).update(account_id=target.pk)
            row.delete()
        else:
            row.account_code = new_code
            row.save(update_fields=['account_code'])

    accounts = {}
    for code, name, account_type, parent_code in ACCOUNT_DEFINITIONS:
        account, _ = Account.objects.get_or_create(
            account_code=code,
            defaults={'account_name': name, 'account_type': account_type, 'is_active': True},
        )
        account.account_name = name
        account.account_type = account_type
        account.is_active = True
        account.save(update_fields=['account_name', 'account_type', 'is_active'])
        accounts[code] = account

    for code, _, _, parent_code in ACCOUNT_DEFINITIONS:
        account = accounts[code]
        account.parent_account = accounts.get(parent_code)
        account.save(update_fields=['parent_account'])

    for account in Account.objects.filter(account_code__startswith='1100.'):
        account.account_code = account.account_code.replace('1100.', '1210.', 1)
        account.parent_account = accounts['1210']
        account.save(update_fields=['account_code', 'parent_account'])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [('accounting', '0008_remove_fiscalyear_bs_year_remove_fiscalyear_end_date_and_more')]
    operations = [migrations.RunPython(rebuild_chart, noop)]
