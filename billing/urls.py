from django.urls import path

from .views import (
    CheckoutCancelView,
    CheckoutSuccessView,
    SubscriptionView,
    add_to_cart,
    cart_view,
    create_cart_checkout,
    create_product_checkout,
    create_subscription_checkout,
    remove_from_cart,
    stripe_webhook,
)

app_name = "billing"

urlpatterns = [
    path("subscribe/", SubscriptionView.as_view(), name="subscribe_page"),
    path("subscribe/start/", create_subscription_checkout, name="subscribe"),
    path("cart/", cart_view, name="cart"),
    path("cart/add/<int:product_id>/", add_to_cart, name="add_to_cart"),
    path("cart/remove/<int:product_id>/", remove_from_cart, name="remove_from_cart"),
    path("cart/checkout/", create_cart_checkout, name="create_cart_checkout"),
    path("checkout/<int:product_id>/", create_product_checkout, name="product_checkout"),
    path("success/", CheckoutSuccessView.as_view(), name="success"),
    path("cancel/", CheckoutCancelView.as_view(), name="cancel"),
    path("webhook/", stripe_webhook, name="webhook"),
]
