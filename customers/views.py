from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.template.loader import render_to_string
from django.http import JsonResponse
from datetime import date

from .models import Customer, Membership, CustomerScheme
from django.db.models import Exists, OuterRef
from .forms import CustomerForm, MembershipForm


# ---------- Customer code auto-generation ----------
def generate_customer_code():
    last = Customer.objects.order_by('-customer_id').first()
    next_id = (last.customer_id + 1) if last else 1
    return f"CUST-{next_id:04d}"


# ---------- List + live search (same pattern as Products) ----------

@login_required
def customer_list(request):
    query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '')   # '', 'ACTIVE', 'INACTIVE'
    member_filter = request.GET.get('member', '')   # '', 'member', 'non_member'

    customers = Customer.objects.annotate(
        has_active_membership=Exists(
            Membership.objects.filter(customer_id=OuterRef('pk'), status='ACTIVE')
        )
    ).order_by('customer_id')

    if query:
        customers = customers.filter(
            Q(customer_code__icontains=query) |
            Q(customer_name__icontains=query) |
            Q(phone__icontains=query)
        )

    if status_filter:
        customers = customers.filter(status=status_filter)

    if member_filter == 'member':
        customers = customers.filter(has_active_membership=True)
    elif member_filter == 'non_member':
        customers = customers.filter(has_active_membership=False)

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        rows_html = render_to_string('customers/customer_rows.html', {'customers': customers})
        return JsonResponse({'rows_html': rows_html})

    context = {
        'customers': customers,
        'query': query,
        'status_filter': status_filter,
        'member_filter': member_filter,
        'total_count': Customer.objects.count(),
        'active_count': Customer.objects.filter(status='ACTIVE').count(),
        'member_count': Customer.objects.filter(membership__status='ACTIVE').distinct().count(),
    }
    return render(request, 'customers/customer_list.html', context)

# ---------- Add ----------
@login_required
def customer_add(request):
    if request.method == 'POST':
        form = CustomerForm(request.POST)
        if form.is_valid():
            customer = form.save(commit=False)
            if not customer.customer_code:
                customer.customer_code = generate_customer_code()
            customer.save()
            messages.success(request, f"Customer {customer.customer_code} registered successfully.")
            return redirect('customer_list')
    else:
        form = CustomerForm(initial={'customer_code': generate_customer_code(), 'status': 'ACTIVE'})

    return render(request, 'customers/customer_form.html', {'form': form, 'title': 'Add Customer'})


# ---------- Edit ----------
@login_required
def customer_edit(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    if request.method == 'POST':
        form = CustomerForm(request.POST, instance=customer)
        if form.is_valid():
            form.save()
            messages.success(request, f"Customer {customer.customer_code} updated.")
            return redirect('customer_list')
    else:
        form = CustomerForm(instance=customer)

    return render(request, 'customers/customer_form.html', {'form': form, 'title': 'Edit Customer'})


# ---------- Deactivate (soft delete — keeps Sales history intact) ----------
@login_required
def customer_deactivate(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    customer.status = 'INACTIVE' if customer.status == 'ACTIVE' else 'ACTIVE'
    customer.save()
    messages.success(request, f"Customer {customer.customer_code} status changed to {customer.status}.")
    return redirect('customer_list')


# ---------- Profile (transaction count, scheme, membership, purchase history) ----------
@login_required
def customer_profile(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    memberships = customer.membership_set.all().order_by('-start_date')

    context = {
        'customer': customer,
        'memberships': memberships,
        'transaction_count': customer.transaction_count,
        'current_scheme': customer.current_scheme,
        'is_member': customer.is_member,
    }
    return render(request, 'customers/customer_profile.html', context)


# ---------- Membership: register / renew ----------
@login_required
def membership_add(request, customer_id):
    customer = get_object_or_404(Customer, pk=customer_id)
    if request.method == 'POST':
        form = MembershipForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                membership = form.save(commit=False)
                membership.customer = customer
                membership.save()
            messages.success(request, f"Membership registered for {customer.customer_name}.")
            return redirect('customer_profile', pk=customer.pk)
    else:
        form = MembershipForm(initial={'status': 'ACTIVE'})

    return render(request, 'customers/membership_form.html', {'form': form, 'customer': customer})


# ---------- Membership: change status (expire/cancel) ----------
@login_required
def membership_update_status(request, pk, new_status):
    membership = get_object_or_404(Membership, pk=pk)
    membership.status = new_status
    membership.save()
    messages.success(request, f"Membership status set to {new_status}.")
    return redirect('customer_profile', pk=membership.customer.pk)


# ---------- Quick search endpoint for Sales screen (Option A / Option B workflow) ----------
@login_required
def customer_search_api(request):
    query = request.GET.get('q', '').strip()
    results = []
    if query:
        customers = Customer.objects.filter(
            Q(customer_code__icontains=query) |
            Q(customer_name__icontains=query) |
            Q(phone__icontains=query),
            status='ACTIVE'
        )[:10]
        results = [
            {
                'id': c.customer_id,
                'code': c.customer_code,
                'name': c.customer_name,
                'phone': c.phone or '',
            }
            for c in customers
        ]
    return JsonResponse({'results': results})