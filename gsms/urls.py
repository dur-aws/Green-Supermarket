"""
URL configuration for gsms project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include

from django.contrib.auth.decorators import login_required
from django.contrib import admin
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required


def root_redirect(request):
    if request.user.is_authenticated:
        if not request.user.is_staff and hasattr(request.user, 'supplier_profile'):
            return redirect('supplier_po_list')
        return redirect('dashboard')  # Redirect logged-in users to home/dashboard
    return redirect('login')          # Redirect guests to login page

urlpatterns = [
    path('admin/', admin.site.urls),
    # Root URL redirect
    path('', root_redirect, name='root'),
    # Accounts / Authentication Module
    path('dashboard/', include('dashboard.urls')),
    # path('accounts/', include(('accounts.urls', 'accounts'), namespace='accounts')),
    # path('', login_required(TemplateView.as_view(template_name='dashboard.html/'), login_url='login'), name='dashboard'),
 
    path('uom/', include('units.urls')),
    path('category/', include('categories.urls')),
    path('supplier/', include('suppliers.urls')),
    path('customer/', include('customers.urls')),
    path('users/', include('accounts.urls')),
    path('activity-log/', include('setting_app.urls')),
    path('purchase/', include('purchases.urls')),
    path('product/', include('products.urls')),
    path('stock/', include('inventory.urls')),
    path('sales/', include('sales.urls')),
]
