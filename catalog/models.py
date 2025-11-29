from django.db import models


class Category(models.Model):
    source_id = models.CharField(max_length=100, unique=True)
    name_en = models.CharField(max_length=255)
    name_kh = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "name_en"]

    def __str__(self):
        return self.name_en


class Product(models.Model):
    source_id = models.CharField(max_length=100, unique=True)
    name_en = models.CharField(max_length=255)
    name_kh = models.CharField(max_length=255, blank=True)
    description_en = models.TextField(blank=True)
    description_kh = models.TextField(blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    image_url = models.URLField(blank=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="products")
    active = models.BooleanField(default=True)
    popular = models.BooleanField(default=False)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "name_en"]

    def __str__(self):
        return self.name_en

# Create your models here.
