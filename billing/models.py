from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

from catalog.models import Product

User = get_user_model()


class Subscription(models.Model):
    STATUS_CHOICES = [
        ("active", "Active"),
        ("incomplete", "Incomplete"),
        ("past_due", "Past due"),
        ("canceled", "Canceled"),
        ("unpaid", "Unpaid"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="subscriptions")
    stripe_customer_id = models.CharField(max_length=255)
    stripe_subscription_id = models.CharField(max_length=255, unique=True)
    price_id = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default="incomplete")
    current_period_end = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.email} subscription ({self.status})"


class Purchase(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="purchases")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="purchases")
    quantity = models.PositiveIntegerField(default=1)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default="usd")
    stripe_checkout_session_id = models.CharField(max_length=255)
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True)
    discount_applied = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ("stripe_checkout_session_id", "product")

    def __str__(self):
        return f"{self.user.email} - {self.product.name_en} x{self.quantity} ({self.amount} {self.currency})"
