from django.contrib import admin

from .models import Category, Product


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name_en", "name_kh", "active", "display_order")
    search_fields = ("name_en", "name_kh", "description")
    list_filter = ("active",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name_en", "category", "price", "active", "popular")
    search_fields = ("name_en", "name_kh", "description_en", "description_kh")
    list_filter = ("active", "popular", "category")
