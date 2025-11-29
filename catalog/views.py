from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .models import Category, Product


def product_list(request):
    categories = Category.objects.prefetch_related("products").all()
    products = Product.objects.filter(active=True).select_related("category")
    return render(
        request,
        "catalog/product_list.html",
        {"categories": categories, "products": products},
    )

# Create your views here.
