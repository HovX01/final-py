def cart_count(request):
    cart = request.session.get("cart", {}) if request else {}
    count = sum(int(qty) for qty in cart.values()) if cart else 0
    return {"cart_item_count": count}
