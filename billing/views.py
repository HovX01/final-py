import json
from datetime import datetime
from decimal import Decimal

import stripe
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView

from accounts.models import User
from catalog.models import Product

from .models import Purchase, Subscription

if settings.STRIPE_SECRET_KEY:
    stripe.api_key = settings.STRIPE_SECRET_KEY


def _require_stripe_key(request):
    if not settings.STRIPE_SECRET_KEY:
        messages.error(request, "Stripe secret key missing; set STRIPE_SECRET_KEY in your environment.")
        return False
    stripe.api_key = settings.STRIPE_SECRET_KEY
    return True


def _get_cart(request):
    return request.session.get("cart", {})


def _save_cart(request, cart):
    request.session["cart"] = cart
    request.session.modified = True


class SubscriptionView(LoginRequiredMixin, TemplateView):
    template_name = "billing/subscribe.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["plan_price"] = settings.PRO_PLAN_PRICE
        ctx["currency"] = settings.DEFAULT_CURRENCY.upper()
        ctx["price_id_configured"] = bool(settings.STRIPE_SUBSCRIPTION_PRICE_ID)
        ctx["is_basic"] = self.request.user.user_type == User.BASIC
        return ctx


@login_required
@require_POST
def create_subscription_checkout(request):
    if not _require_stripe_key(request):
        return redirect("home")
    if not request.user.is_verified:
        messages.error(request, "Verify your email before subscribing.")
        return redirect("billing:subscribe_page")
    price_id = settings.STRIPE_SUBSCRIPTION_PRICE_ID

    line_item = (
        {"price": price_id, "quantity": 1}
        if price_id
        else {
            "price_data": {
                "currency": settings.DEFAULT_CURRENCY,
                "product_data": {"name": "Pro Plan"},
                "recurring": {"interval": "month"},
                "unit_amount": int(Decimal(str(settings.PRO_PLAN_PRICE)) * 100),
            },
            "quantity": 1,
        }
    )

    session = stripe.checkout.Session.create(
        mode="subscription",
        customer_email=request.user.email,
        line_items=[line_item],
        success_url=f"{settings.SITE_URL}{reverse('billing:success')}?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{settings.SITE_URL}{reverse('billing:cancel')}",
        metadata={
            "user_id": str(request.user.id),
            "price_id": price_id,
            "type": "subscription",
        },
    )
    return redirect(session.url)


@login_required
@require_POST
def create_product_checkout(request, product_id):
    if not _require_stripe_key(request):
        return redirect("catalog:product_list")
    if not request.user.is_verified:
        messages.error(request, "Verify your email before purchasing.")
        return redirect("accounts:profile")

    product = get_object_or_404(Product, pk=product_id, active=True)
    price = Decimal(product.price)
    discount_applied = False
    if getattr(request.user, "user_type", User.BASIC) == User.PRO:
        discount_applied = True
        price = (price * Decimal("0.8")).quantize(Decimal("0.01"))

    session = stripe.checkout.Session.create(
        mode="payment",
        customer_email=request.user.email,
        line_items=[
            {
                "price_data": {
                    "currency": settings.DEFAULT_CURRENCY,
                    "product_data": {"name": product.name_en, "description": product.description_en[:200]},
                    "unit_amount": int((price * 100).quantize(Decimal("1"))),
                },
                "quantity": 1,
            }
        ],
        success_url=f"{settings.SITE_URL}{reverse('billing:success')}?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{settings.SITE_URL}{reverse('billing:cancel')}",
        metadata={
            "user_id": str(request.user.id),
            "product_id": str(product.id),
            "quantity": "1",
            "discount_applied": str(discount_applied).lower(),
            "type": "product",
        },
    )
    return redirect(session.url)


class CheckoutSuccessView(TemplateView):
    template_name = "billing/success.html"

    def get(self, request, *args, **kwargs):
        session_id = request.GET.get("session_id")
        if session_id and settings.STRIPE_SECRET_KEY:
            try:
                session = stripe.checkout.Session.retrieve(session_id)
                _handle_checkout_completed(session)
            except stripe.error.StripeError:
                messages.warning(request, "Could not verify payment status from Stripe.")
        if "cart" in request.session:
            request.session.pop("cart")
            request.session.modified = True
        return super().get(request, *args, **kwargs)


class CheckoutCancelView(TemplateView):
    template_name = "billing/cancel.html"


@login_required
@require_POST
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, pk=product_id, active=True)
    cart = _get_cart(request)
    cart[str(product_id)] = cart.get(str(product_id), 0) + 1
    _save_cart(request, cart)
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"ok": True, "message": f"Added {product.name_en} to cart.", "cart_count": sum(cart.values())})
    messages.success(request, f"Added {product.name_en} to cart.")
    return redirect("catalog:product_list")


@login_required
@require_POST
def remove_from_cart(request, product_id):
    cart = _get_cart(request)
    if str(product_id) in cart:
        cart.pop(str(product_id))
        _save_cart(request, cart)
        messages.info(request, "Removed item from cart.")
    return redirect("billing:cart")


@login_required
def cart_view(request):
    cart = _get_cart(request)
    product_ids = list(map(int, cart.keys()))
    products = {p.id: p for p in Product.objects.filter(id__in=product_ids, active=True)}
    items = []
    total = Decimal("0")
    is_pro = getattr(request.user, "user_type", User.BASIC) == User.PRO
    for pid_str, qty in cart.items():
        pid = int(pid_str)
        product = products.get(pid)
        if not product:
            continue
        qty = int(qty)
        price = Decimal(product.price)
        line_total = price * qty
        total += line_total
        items.append(
            {
                "product": product,
                "quantity": qty,
                "price": price,
                "line_total": line_total,
            }
        )
    discount_total = (total * Decimal("0.8")).quantize(Decimal("0.01")) if is_pro else total
    return render(
        request,
        "billing/cart.html",
        {
            "items": items,
            "total": total,
            "discount_total": discount_total,
            "is_pro": is_pro,
        },
    )


@login_required
@require_POST
def create_cart_checkout(request):
    cart = _get_cart(request)
    if not cart:
        messages.error(request, "Your cart is empty.")
        return redirect("catalog:product_list")
    if not request.user.is_verified:
        messages.error(request, "Verify your email before purchasing.")
        return redirect("accounts:profile")
    if not _require_stripe_key(request):
        return redirect("billing:cart")

    product_ids = list(map(int, cart.keys()))
    products = {p.id: p for p in Product.objects.filter(id__in=product_ids, active=True)}
    line_items = []
    cart_entries = []
    is_pro = getattr(request.user, "user_type", User.BASIC) == User.PRO
    for pid_str, qty in cart.items():
        pid = int(pid_str)
        product = products.get(pid)
        if not product:
            continue
        qty = int(qty)
        price = Decimal(product.price)
        if is_pro:
            price = (price * Decimal("0.8")).quantize(Decimal("0.01"))
        line_items.append(
            {
                "price_data": {
                    "currency": settings.DEFAULT_CURRENCY,
                    "product_data": {"name": product.name_en, "description": product.description_en[:200]},
                    "unit_amount": int((price * 100).quantize(Decimal("1"))),
                },
                "quantity": qty,
            }
        )
        cart_entries.append(f"{pid}:{qty}")

    if not line_items:
        messages.error(request, "No valid items to purchase.")
        return redirect("catalog:product_list")

    session = stripe.checkout.Session.create(
        mode="payment",
        customer_email=request.user.email,
        line_items=line_items,
        success_url=f"{settings.SITE_URL}{reverse('billing:success')}?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{settings.SITE_URL}{reverse('billing:cancel')}",
        metadata={
            "user_id": str(request.user.id),
            "type": "product_cart",
            "cart": "|".join(cart_entries),
            "discount_applied": str(is_pro).lower(),
        },
    )
    return redirect(session.url)


@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
    event = None
    if settings.STRIPE_WEBHOOK_SECRET:
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)
        except (ValueError, stripe.error.SignatureVerificationError):
            return HttpResponseBadRequest("Invalid webhook signature")
    else:
        try:
            event = json.loads(payload)
        except json.JSONDecodeError:
            return HttpResponseBadRequest("Invalid payload")

    event_type = event.get("type")
    data_object = event.get("data", {}).get("object", {})

    if event_type == "checkout.session.completed":
        _handle_checkout_completed(data_object)
    elif event_type in ("customer.subscription.updated", "customer.subscription.deleted"):
        _handle_subscription_updated(data_object)

    return HttpResponse(status=200)


def _handle_checkout_completed(session):
    mode = session.get("mode")
    metadata = session.get("metadata") or {}
    user_id = metadata.get("user_id")
    user = User.objects.filter(pk=user_id).first()
    if not user:
        return

    if mode == "subscription":
        subscription_id = session.get("subscription")
        if not subscription_id:
            return
        Subscription.objects.update_or_create(
            stripe_subscription_id=subscription_id,
            defaults={
                "user": user,
                "stripe_customer_id": session.get("customer") or "",
                "price_id": metadata.get("price_id", ""),
                "status": "active",
                "current_period_end": _timestamp_to_dt(session.get("expires_at")),
            },
        )
        if user.user_type != User.PRO:
            user.user_type = User.PRO
            user.save(update_fields=["user_type"])
    elif mode == "payment":
        cart_map = metadata.get("cart")
        discount_applied = metadata.get("discount_applied") == "true"
        if metadata.get("type") == "product_cart" and cart_map:
            entries = [entry.split(":") for entry in cart_map.split("|") if ":" in entry]
            for pid_str, qty_str in entries:
                product = Product.objects.filter(pk=pid_str).first()
                if not product:
                    continue
                qty = int(qty_str)
                price = Decimal(product.price)
                if discount_applied:
                    price = (price * Decimal("0.8")).quantize(Decimal("0.01"))
                Purchase.objects.update_or_create(
                    stripe_checkout_session_id=session.get("id"),
                    product=product,
                    defaults={
                        "user": user,
                        "product": product,
                        "quantity": qty,
                        "amount": (price * qty).quantize(Decimal("0.01")),
                        "currency": session.get("currency", settings.DEFAULT_CURRENCY),
                        "stripe_payment_intent_id": session.get("payment_intent", ""),
                        "discount_applied": discount_applied,
                    },
                )
        else:
            product_id = metadata.get("product_id")
            product = Product.objects.filter(pk=product_id).first()
            if not product:
                return
            qty = int(metadata.get("quantity", "1"))
            price = Decimal(product.price)
            if metadata.get("discount_applied") == "true":
                price = (price * Decimal("0.8")).quantize(Decimal("0.01"))
            Purchase.objects.update_or_create(
                stripe_checkout_session_id=session.get("id"),
                product=product,
                defaults={
                    "user": user,
                    "product": product,
                    "quantity": qty,
                    "amount": (price * qty).quantize(Decimal("0.01")),
                    "currency": session.get("currency", settings.DEFAULT_CURRENCY),
                    "stripe_payment_intent_id": session.get("payment_intent", ""),
                    "discount_applied": metadata.get("discount_applied") == "true",
                },
            )


def _handle_subscription_updated(subscription):
    sub_id = subscription.get("id")
    if not sub_id:
        return
    Subscription.objects.update_or_create(
        stripe_subscription_id=sub_id,
        defaults={
            "stripe_customer_id": subscription.get("customer", ""),
            "status": subscription.get("status", "incomplete"),
            "current_period_end": _timestamp_to_dt(subscription.get("current_period_end")),
        },
    )


def _timestamp_to_dt(value):
    if not value:
        return None
    try:
        return datetime.fromtimestamp(int(value), tz=timezone.utc)
    except (ValueError, TypeError):
        return None

# Create your views here.
