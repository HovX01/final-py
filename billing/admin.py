from django.contrib import admin

from .models import Purchase, Subscription


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "stripe_subscription_id",
        "status",
        "price_id",
        "current_period_end",
    )
    search_fields = ("stripe_subscription_id", "user__email")
    list_filter = ("status",)


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ("user", "product", "quantity", "amount", "currency", "discount_applied", "created_at")
    search_fields = ("user__email", "product__name_en", "stripe_checkout_session_id")
    list_filter = ("discount_applied",)
