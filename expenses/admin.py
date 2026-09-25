from django.contrib import admin

from .models import Expense


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
	list_display = ('expense_date', 'expense_type', 'amount', 'fiscal_year', 'journal_entry')
	list_filter = ('expense_type', 'fiscal_year')
	search_fields = ('description', 'reference_number')
