import logging

import requests
from django.core.management.base import BaseCommand, CommandError
from decimal import Decimal

from catalog.models import Category, Product

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Import products and categories from the external API"

    def add_arguments(self, parser):
        parser.add_argument(
            "--url",
            default="https://ousa-food.vercel.app/api/products",
            help="Endpoint returning categories and products JSON",
        )

    def handle(self, *args, **options):
        url = options["url"]
        self.stdout.write(f"Fetching data from {url}")
        try:
            resp = requests.get(url, timeout=20)
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise CommandError(f"Failed to fetch data: {exc}") from exc

        data = resp.json()
        if not isinstance(data, dict) or "categories" not in data or "products" not in data:
            raise CommandError("Unexpected payload shape; expected 'categories' and 'products'.")

        category_map = self._import_categories(data["categories"])
        self._import_products(data["products"], category_map)

    def _import_categories(self, categories):
        created = updated = 0
        category_map = {}
        for item in categories:
            obj, was_created = Category.objects.update_or_create(
                source_id=item["id"],
                defaults={
                    "name_en": item.get("name_en", "") or "",
                    "name_kh": item.get("name_kh", "") or "",
                    "description": item.get("description", "") or "",
                    "active": bool(item.get("active", True)),
                    "display_order": item.get("display_order") or 0,
                },
            )
            category_map[obj.source_id] = obj
            created += 1 if was_created else 0
            updated += 0 if was_created else 1
        self.stdout.write(self.style.SUCCESS(f"Categories - created: {created}, updated: {updated}"))
        return category_map

    def _import_products(self, products, category_map):
        created = updated = 0
        for item in products:
            category = category_map.get(item.get("category_id"))
            if not category:
                logger.warning("Skipping product %s due to missing category %s", item.get("id"), item.get("category_id"))
                continue
            obj, was_created = Product.objects.update_or_create(
                source_id=item["id"],
                defaults={
                    "name_en": item.get("name_en", "") or "",
                    "name_kh": item.get("name_kh", "") or "",
                    "description_en": item.get("description_en", "") or "",
                    "description_kh": item.get("description_kh", "") or "",
                    "price": Decimal(str(item.get("price") or 0)),
                    "image_url": item.get("image_url", "") or "",
                    "category": category,
                    "active": bool(item.get("active", True)),
                    "popular": bool(item.get("popular", False)),
                    "display_order": item.get("display_order") or 0,
                },
            )
            created += 1 if was_created else 0
            updated += 0 if was_created else 1
        self.stdout.write(self.style.SUCCESS(f"Products - created: {created}, updated: {updated}"))
