from django.urls import path

from .views import product_list

app_name = "catalog"

urlpatterns = [
    path("products/", product_list, name="product_list"),
]
