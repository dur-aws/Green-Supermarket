from django.shortcuts import render

# Create your views here.
from django.shortcuts import render, redirect, get_object_or_404
from .models import Category
from django.contrib.auth.decorators import login_required
from .forms import CategoryForm
from django.db.models import Q, ProtectedError
from django.core.paginator import Paginator

@login_required
def category_list(request):
    query = request.GET.get('q')
    if query:
        categories = Category.objects.filter(name__icontains=query)
    else:
        categories = Category.objects.all()

    paginator = Paginator(categories, 10)  # 10 per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'categories/category_list.html', {
        'page_obj': page_obj,
        'query': query,
        'title': 'Categories'
    })


# Add new category
@login_required
def category_add(request):
    if request.method == "POST":
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save(commit=False)
        category.save()
        return redirect('category_list')
    form = CategoryForm() 
    return render(request, 'categories/category_form.html', {'form': form, 'title': 'Add Category'})


# Update category
@login_required
def category_edit(request, id):
    category = get_object_or_404(Category, id=id)
    if request.method == "POST":

        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            category = form.save(commit=False)
        category.save()
        return redirect("category_list")
    else:
        form - CategoryForm(instance=category)
    return render(request, "categories/category_form.html", {'form': form, 'title': 'Edit Category'})


@login_required
def category_toggle_status(request, pk):
    """Soft delete / reactivate — the safe default for products
    that already have transaction history."""
    p = get_object_or_404(Category, pk=pk)
    Category.status = 0 if Category.status == 1 else 1
    Category.save()
   
    return redirect('category_list')
