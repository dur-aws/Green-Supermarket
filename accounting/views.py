from decimal import Decimal

from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db import transaction
from django.forms import inlineformset_factory
from django.views.decorators.http import require_POST
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.views.generic import ListView, TemplateView
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from accounts.mixins import RBACPermissionMixin
from .models import Account, FiscalYear, JournalEntry, JournalItem
from .forms import FiscalYearForm, JournalEntryForm, JournalItemForm
from .services import (
    AccountingError, AccountingService, FiscalYearService, GeneralLedgerError,
    GeneralLedgerService, TrialBalanceError, TrialBalanceService,
)

JournalItemFormSet = inlineformset_factory(
    JournalEntry, JournalItem, form=JournalItemForm, extra=2, can_delete=True
)

def fiscal_year_list(request):
    fiscal_years = FiscalYear.objects.all()
    return render(request, 'accounting/fy_list.html', {'fiscal_years': fiscal_years})


def fiscal_year_create(request):
    if request.method == 'POST':
        form = FiscalYearForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Fiscal Year created successfully.")
            return redirect('fiscal_year_list')
    else:
        # Pre-fill defaults using the service
        defaults = FiscalYearService.get_current_fy_info()
        form = FiscalYearForm(initial=defaults)
        
    return render(request, 'accounting/fy_form.html', {'form': form, 'title': 'Create Fiscal Year'})

def fiscal_year_activate(request, pk):
    FiscalYearService.set_active_fiscal_year(pk)
    messages.success(request, "Active fiscal year updated.")
    return redirect('fiscal_year_list')

def fiscal_year_toggle_close(request, pk):
    fy = FiscalYearService.toggle_close_status(pk)
    status = "closed" if fy.is_closed else "re-opened"
    messages.info(request, f"Fiscal Year {fy.name} has been {status}.")
    return redirect('fiscal_year_list')

class JournalListView(RBACPermissionMixin, ListView):
    model = JournalEntry
    template_name = 'journal.html'
    context_object_name = 'journals'

    paginate_by = 15
    module_name = 'accounting'
    required_permission = 'view'

    # Latest journal entry first
    ordering = ['-entry_id']

    

    def get_queryset(self):
        queryset = (
            JournalEntry.objects
            .select_related('fiscal_year', 'created_by', 'posted_by', 'reversed_by')
            .prefetch_related('items__account')
            .order_by('-entry_id')
        )

        # Date filters
        from_date = self.request.GET.get('from_date')
        to_date = self.request.GET.get('to_date')

        if from_date:
            queryset = queryset.filter(
                entry_date__gte=from_date
            )

        if to_date:
            queryset = queryset.filter(
                entry_date__lte=to_date
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['from_date'] = self.request.GET.get('from_date', '')
        context['to_date'] = self.request.GET.get('to_date', '')
        return context


@login_required
@permission_required('accounting.add_journalentry', raise_exception=True)
def journal_create(request):
    entry = JournalEntry(
        entry_date=timezone.now().date(),
        reference_type='MANUAL',
        fiscal_year=FiscalYear.objects.filter(is_active=True).first(),
        created_by=request.user,
    )
    return journal_edit(request, entry=entry, is_new=True)


@login_required
@permission_required('accounting.change_journalentry', raise_exception=True)
def journal_edit(request, pk=None, entry=None, is_new=False):
    if entry is None:
        entry = get_object_or_404(JournalEntry, pk=pk)
    if not is_new and entry.status != JournalEntry.STATUS_DRAFT:
        messages.error(request, 'Only draft journal entries can be edited.')
        return redirect('journal_view')
    if is_new:
        entry.created_by = request.user
    form = JournalEntryForm(request.POST or None, instance=entry)
    formset = JournalItemFormSet(request.POST or None, instance=entry)
    action = request.POST.get('action') if request.method == 'POST' else 'draft'
    if request.method == 'POST' and form.is_valid() and formset.is_valid():
        with transaction.atomic():
            saved_entry = form.save(commit=False)
            saved_entry.reference_type = 'MANUAL'
            saved_entry.created_by = entry.created_by or request.user
            saved_entry.save()
            formset.instance = saved_entry
            formset.save()
            if action == 'post':
                try:
                    AccountingService.post_journal_entry(saved_entry, user=request.user)
                except AccountingError as exc:
                    form.add_error(None, str(exc))
                else:
                    messages.success(request, f'JV-{saved_entry.entry_id} posted.')
                    return redirect('journal_view')
            elif action == 'delete':
                saved_entry.delete()
                messages.success(request, 'Draft journal entry deleted.')
                return redirect('journal_view')
            else:
                messages.success(request, f'JV-{saved_entry.entry_id} saved as draft.')
                return redirect('journal_view')
    return render(request, 'accounting/journal_form.html', {'form': form, 'formset': formset, 'entry': entry})


@login_required
@permission_required('accounting.change_journalentry', raise_exception=True)
@require_POST
def journal_post(request, pk):
    entry = get_object_or_404(JournalEntry, pk=pk)
    try:
        AccountingService.post_journal_entry(entry, user=request.user)
        messages.success(request, f'JV-{entry.entry_id} posted.')
    except AccountingError as exc:
        messages.error(request, str(exc))
    return redirect('journal_view')


@login_required
@permission_required('accounting.change_journalentry', raise_exception=True)
@require_POST
def journal_reverse(request, pk):
    entry = get_object_or_404(JournalEntry, pk=pk)
    try:
        reversal = AccountingService.reverse_journal_entry(entry, user=request.user)
        messages.success(request, f'JV-{entry.entry_id} reversed with JV-{reversal.entry_id}.')
    except AccountingError as exc:
        messages.error(request, str(exc))
    return redirect('journal_view')


@login_required
@permission_required('accounting.delete_journalentry', raise_exception=True)
@require_POST
def journal_delete(request, pk):
    entry = get_object_or_404(JournalEntry, pk=pk)
    if entry.status != JournalEntry.STATUS_DRAFT:
        messages.error(request, 'Only draft journal entries can be deleted.')
    else:
        entry.delete()
        messages.success(request, 'Draft journal entry deleted.')
    return redirect('journal_view')


class ChartOfAccountsView(RBACPermissionMixin, TemplateView):
    template_name = 'chart_of_accounts.html'
    module_name = 'accounting'
    required_permission = 'view'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        accounts = list(Account.objects.filter(is_active=True).order_by('account_code'))
        by_parent = {}
        for account in accounts:
            by_parent.setdefault(account.parent_account_id, []).append(account)

        chart_rows = []

        def add_children(parent_id, depth=0):
            for account in by_parent.get(parent_id, []):
                chart_rows.append({'account': account, 'depth': depth})
                add_children(account.pk, depth + 1)

        add_children(None)
        context['chart_rows'] = chart_rows
        return context


class GeneralLedgerView(RBACPermissionMixin, ListView):
    template_name = 'general_ledger.html'
    context_object_name = 'ledger_rows'
    paginate_by = 25
    module_name = 'accounting'
    required_permission = 'view'
   

    def get_queryset(self):
        # The report service owns filtering and pagination data preparation.
        return []

    def get_report(self):
        account_id = self.request.GET.get('account') or Account.objects.filter(is_active=True).values_list('pk', flat=True).first()
        return GeneralLedgerService.get_report(
            fiscal_year_id=self.request.GET.get('fiscal_year') or None,
            account_id=account_id,
            from_date=self.request.GET.get('from_date', '').strip(),
            to_date=self.request.GET.get('to_date', '').strip(),
            search=self.request.GET.get('q', '').strip(),
            
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            report = self.get_report()
            page = Paginator(report['rows'], self.paginate_by).get_page(self.request.GET.get('page'))
        except GeneralLedgerError as exc:
            messages.error(self.request, str(exc))
            report = {
                'fiscal_year': FiscalYear.objects.filter(pk=self.request.GET.get('fiscal_year')).first() or FiscalYear.objects.filter(is_active=True).first(),
                'account': Account.objects.filter(pk=self.request.GET.get('account')).first(),
                'accounts': Account.objects.filter(is_active=True).order_by('account_code'),
                'from_date': self.request.GET.get('from_date', ''),
                'to_date': self.request.GET.get('to_date', ''),
                'search': self.request.GET.get('q', ''),
                'normal_balance': 'debit',
                'opening_balance': Decimal('0.00'),
                'opening_side': 'Dr',
                'rows': [],
                'total_debit': Decimal('0.00'),
                'total_credit': Decimal('0.00'),
                'closing_balance': Decimal('0.00'),
                'closing_side': 'Dr',
            }
            page = Paginator([], self.paginate_by).get_page(1)

        context.update(report)
        context.update({
            'fiscal_years': FiscalYear.objects.order_by('-start_date_bs'),
            'page_obj': page,
            'is_paginated': page.has_other_pages(),
            'filter_query': self.request.GET.copy(),
        })
        context['filter_query'].pop('page', None)
        context['filter_query'] = context['filter_query'].urlencode()
        return context

    def render_to_response(self, context, **response_kwargs):
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'rows_html': render_to_string('_ledger_rows.html', context, request=self.request),
                'total_debit': str(context['total_debit']),
                'total_credit': str(context['total_credit']),
                'closing_balance': str(context['closing_balance']),
                'closing_side': context['closing_side'],
                'count': len(context['rows']),
            })
        return super().render_to_response(context, **response_kwargs)


class TrialBalanceView(RBACPermissionMixin, ListView):
    template_name = 'accounting/trial_balance.html'
    context_object_name = 'trial_balance_rows'
    paginate_by = 25
    module_name = 'accounting'
    required_permission = 'view'

    def get_queryset(self):
        return []

    def get_report(self):
        return TrialBalanceService.get_report(
            fiscal_year_id=self.request.GET.get('fiscal_year') or None,
            from_date=self.request.GET.get('from_date', '').strip(),
            to_date=self.request.GET.get('to_date', '').strip(),
            search=self.request.GET.get('q', '').strip(),
            account_type=self.request.GET.get('account_type', '').strip(),
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            report = self.get_report()
            page = Paginator(report['rows'], self.paginate_by).get_page(self.request.GET.get('page'))
        except TrialBalanceError as exc:
            messages.error(self.request, str(exc))
            report = {
                'fiscal_year': FiscalYear.objects.filter(pk=self.request.GET.get('fiscal_year')).first() or FiscalYear.objects.filter(is_active=True).first(),
                'from_date': self.request.GET.get('from_date', ''),
                'to_date': self.request.GET.get('to_date', ''),
                'search': self.request.GET.get('q', ''),
                'account_type': self.request.GET.get('account_type', ''),
                'account_types': Account.ACCOUNT_TYPE_CHOICES,
                'rows': [], 'total_debit': Decimal('0.00'), 'total_credit': Decimal('0.00'),
                'difference': Decimal('0.00'), 'is_balanced': True,
            }
            page = Paginator([], self.paginate_by).get_page(1)
        context.update(report)
        context.update({
            'fiscal_years': FiscalYear.objects.order_by('-start_date_bs'),
            'page_obj': page,
            'is_paginated': page.has_other_pages(),
            'filter_query': self.request.GET.copy(),
        })
        context['filter_query'].pop('page', None)
        context['filter_query'] = context['filter_query'].urlencode()
        return context

    def render_to_response(self, context, **response_kwargs):
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'rows_html': render_to_string('accounting/_trial_balance_rows.html', context, request=self.request),
                'total_debit': str(context['total_debit']),
                'total_credit': str(context['total_credit']),
                'difference': str(context['difference']),
                'is_balanced': context['is_balanced'],
                'count': len(context['rows']),
            })
        return super().render_to_response(context, **response_kwargs)


class TrialBalancePDFView(TrialBalanceView):
    def get(self, request, *args, **kwargs):
        context = self.get_context_data()
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'inline; filename="trial-balance.pdf"'
        document = SimpleDocTemplate(response, pagesize=landscape(A4), rightMargin=10 * mm, leftMargin=10 * mm, topMargin=10 * mm, bottomMargin=10 * mm)
        styles = getSampleStyleSheet()
        right = ParagraphStyle('TrialBalanceRight', parent=styles['Normal'], alignment=TA_RIGHT, fontSize=8)
        data = [['Account', 'Type', 'Opening', 'Period Debit', 'Period Credit', 'Closing Debit', 'Closing Credit']]
        for row in context['rows']:
            data.append([
                f"{row['account'].account_code} - {row['account'].account_name}", row['account'].get_account_type_display(),
                Paragraph(f"{row['opening_balance']:.2f} {row['opening_side']}", right),
                Paragraph(f"{row['period_debit']:.2f}", right), Paragraph(f"{row['period_credit']:.2f}", right),
                Paragraph(f"{row['closing_debit']:.2f}", right), Paragraph(f"{row['closing_credit']:.2f}", right),
            ])
        data.append(['Total', '', '', Paragraph(f"{context['total_debit']:.2f}", right), Paragraph(f"{context['total_credit']:.2f}", right), '', ''])
        table = Table(data, colWidths=[65 * mm, 30 * mm, 30 * mm, 30 * mm, 30 * mm, 30 * mm, 30 * mm], repeatRows=1)
        table.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), 0.35, colors.HexColor('#9aa39a')), ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e8f0e8')), ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'), ('ALIGN', (2, 1), (-1, -1), 'RIGHT')]))
        document.build([Paragraph('Trial Balance', styles['Title']), table])
        return response


class GeneralLedgerPDFView(GeneralLedgerView):
    """Export the same filtered ledger data as the screen to a PDF report."""

    def get(self, request, *args, **kwargs):
        self.object_list = []
        context = self.get_context_data()
        report = context
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'inline; filename="general-ledger.pdf"'
        document = SimpleDocTemplate(
            response, pagesize=landscape(A4), rightMargin=10 * mm,
            leftMargin=10 * mm, topMargin=10 * mm, bottomMargin=10 * mm,
        )
        styles = getSampleStyleSheet()
        title = ParagraphStyle('LedgerTitle', parent=styles['Title'], alignment=TA_CENTER, fontSize=15)
        meta = ParagraphStyle('LedgerMeta', parent=styles['Normal'], alignment=TA_CENTER, fontSize=9)
        right = ParagraphStyle('LedgerRight', parent=styles['Normal'], alignment=TA_RIGHT, fontSize=8)
        fiscal_year = report.get('fiscal_year')
        account = report.get('account')
        story = [
            Paragraph('GSM', title),
            Paragraph('General Ledger', title),
            Paragraph(
                f'Fiscal Year: {fiscal_year.name if fiscal_year else "-"} | '
                f'Account: {account.account_code if account else "-"} - {account.account_name if account else "-"} | '
                f'Date Range: {report.get("from_date", "-")} to {report.get("to_date", "-")}', meta
            ),
            Spacer(1, 5 * mm),
            Paragraph(
                f'Opening Balance: {report["opening_balance"]:.2f} {report["opening_side"]}',
                styles['Normal'],
            ),
        ]
        data = [['Date (BS)', 'Journal Entry No.', 'Reference No. / Type', 'Particulars', 'Debit', 'Credit', 'Running Balance']]
        for row in report['rows']:
            data.append([
                row['date_bs'], row['journal_no'], row['reference'], row['particulars'],
                Paragraph(f'{row["debit"]:.2f}', right), Paragraph(f'{row["credit"]:.2f}', right),
                Paragraph(f'{row["running_balance"]:.2f} {row["running_side"]}', right),
            ])
        data.append(['', '', '', 'Total', Paragraph(f'{report["total_debit"]:.2f}', right), Paragraph(f'{report["total_credit"]:.2f}', right), ''])
        data.append(['', '', '', 'Closing Balance', '', '', Paragraph(f'{report["closing_balance"]:.2f} {report["closing_side"]}', right)])
        table = Table(data, colWidths=[22 * mm, 29 * mm, 40 * mm, 76 * mm, 25 * mm, 25 * mm, 35 * mm], repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e8f0e8')),
            ('GRID', (0, 0), (-1, -1), 0.35, colors.HexColor('#9aa39a')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (4, 1), (-1, -1), 'RIGHT'),
            ('SPAN', (0, -2), (2, -2)),
            ('SPAN', (0, -1), (2, -1)),
            ('FONTNAME', (3, -2), (-1, -1), 'Helvetica-Bold'),
        ]))
        story.append(table)
        document.build(story)
        return response
# class TrialBalanceView(RBACPermissionMixin, ListView):
#     template_name = 'trial_balance.html'
#     context_object_name = 'trialbalances'
#     paginate_by = 25
#     module_name = 'accounting'
#     required_permission = 'view'

#     def get_queryset(self):
#         # The report service owns filtering and pagination data preparation.
#         return []

#     def get_report(self):
#         account_id = self.request.GET.get('account') or Account.objects.filter(is_active=True).values_list('pk', flat=True).first()
#         return GeneralLedgerService.get_report(
#             fiscal_year_id=self.request.GET.get('fiscal_year') or None,
#             account_id=account_id,
#             from_date=self.request.GET.get('from_date', '').strip(),
#             to_date=self.request.GET.get('to_date', '').strip(),
#             search=self.request.GET.get('q', '').strip(),
#         )

#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         try:
#             report = self.get_report()
#             page = Paginator(report['rows'], self.paginate_by).get_page(self.request.GET.get('page'))
#         except GeneralLedgerError as exc:
#             messages.error(self.request, str(exc))
#             report = {
#                 'fiscal_year': FiscalYear.objects.filter(pk=self.request.GET.get('fiscal_year')).first() or FiscalYear.objects.filter(is_active=True).first(),
#                 'account': Account.objects.filter(pk=self.request.GET.get('account')).first(),
#                 'accounts': Account.objects.filter(is_active=True).order_by('account_code'),
#                 'from_date': self.request.GET.get('from_date', ''),
#                 'to_date': self.request.GET.get('to_date', ''),
#                 'search': self.request.GET.get('q', ''),
#                 'normal_balance': 'debit',
#                 'opening_balance': Decimal('0.00'),
#                 'opening_side': 'Dr',
#                 'rows': [],
#                 'total_debit': Decimal('0.00'),
#                 'total_credit': Decimal('0.00'),
#                 'closing_balance': Decimal('0.00'),
#                 'closing_side': 'Dr',
#             }
#             page = Paginator([], self.paginate_by).get_page(1)

#         context.update(report)
#         context.update({
#             'fiscal_years': FiscalYear.objects.order_by('-start_date_bs'),
#             'page_obj': page,
#             'is_paginated': page.has_other_pages(),
#             'filter_query': self.request.GET.copy(),
#         })
#         context['filter_query'].pop('page', None)
#         context['filter_query'] = context['filter_query'].urlencode()
#         return context

#     def render_to_response(self, context, **response_kwargs):
#         if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
#             return JsonResponse({
#                 'rows_html': render_to_string('_ledger_rows.html', context, request=self.request),
#                 'total_debit': str(context['total_debit']),
#                 'total_credit': str(context['total_credit']),
#                 'closing_balance': str(context['closing_balance']),
#                 'closing_side': context['closing_side'],
#                 'count': len(context['rows']),
#             })
#         return super().render_to_response(context, **response_kwargs)
