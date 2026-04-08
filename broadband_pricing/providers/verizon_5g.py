"""Verizon 5G Home (FWA) pricing scraper."""

import re
from typing import Optional

from bs4 import BeautifulSoup

from broadband_pricing.models import Plan, Location
from broadband_pricing.providers.base import BaseProvider
from broadband_pricing.http_client import get_api_headers


class Verizon5GProvider(BaseProvider):
    name = "verizon_5g"
    provider_type = "fwa"

    HOME_URL = "https://www.verizon.com/5g/home/"
    API_URL = "https://www.verizon.com/inhome/api/product/5g-home/plans"

    def scrape_plans(self, location: Location) -> Optional[list[Plan]]:
        plans = self._try_api(location)
        if plans:
            return plans

        plans = self._try_web_scrape()
        if plans:
            return plans

        return self._try_playwright()

    def _try_api(self, location: Location) -> Optional[list[Plan]]:
        try:
            headers = get_api_headers(referer="https://www.verizon.com/5g/home/")
            resp = self.session.get(
                self.API_URL,
                headers=headers,
                params={
                    "streetAddress": location.address,
                    "city": location.city,
                    "state": location.state,
                    "zipCode": location.zip_code,
                },
            )
            if resp and resp.status_code == 200:
                data = resp.json()
                plans = []
                for product in data.get("products", data.get("plans", [])):
                    name = product.get("name", "")
                    price = product.get("price", product.get("monthlyPrice", 0))
                    speed = product.get("downloadSpeed", 300)
                    if name and price:
                        plans.append(
                            Plan(
                                provider="Verizon 5G Home",
                                provider_type="fwa",
                                plan_name=name,
                                speed_down=int(speed),
                                speed_up=int(product.get("uploadSpeed", 20)),
                                monthly_price=float(price),
                            )
                        )
                if plans:
                    return plans
        except Exception as e:
            self.logger.debug(f"Verizon 5G Home API failed: {e}")
        return None

    def _try_web_scrape(self) -> Optional[list[Plan]]:
        try:
            resp = self.session.get(self.HOME_URL)
            if not resp:
                resp = self.session.get_with_cloudscraper(self.HOME_URL)
            if not resp:
                return None

            soup = BeautifulSoup(resp.text, "lxml")
            plan_cards = soup.find_all(
                ["div", "li", "section"],
                class_=re.compile(r"plan|offer|package|card|tier|pricing", re.I),
            )
            plans = []
            for card in plan_cards:
                text = card.get_text(separator=" ")
                price_match = re.search(r"\$(\d+(?:\.\d{2})?)\s*/\s*mo", text)
                if price_match:
                    price = float(price_match.group(1))
                    if 20 <= price <= 100:
                        is_plus = "plus" in text.lower() or price < 50
                        plans.append(
                            Plan(
                                provider="Verizon 5G Home",
                                provider_type="fwa",
                                plan_name="Verizon 5G Home Plus"
                                if is_plus
                                else "Verizon 5G Home",
                                speed_down=300 if is_plus else 85,
                                speed_up=20,
                                monthly_price=price,
                            )
                        )
            if plans:
                return plans
        except Exception as e:
            self.logger.debug(f"Verizon 5G web scrape failed: {e}")
        return None

    def _try_playwright(self) -> Optional[list[Plan]]:
        html = self.session.get_with_playwright(self.HOME_URL)
        if not html:
            return None
        try:
            soup = BeautifulSoup(html, "lxml")
            text = soup.get_text()
            prices = re.findall(r"\$(\d+(?:\.\d{2})?)\s*/\s*mo", text)
            if prices:
                plans = []
                for p in prices:
                    price = float(p)
                    if 20 <= price <= 100:
                        plans.append(
                            Plan(
                                provider="Verizon 5G Home",
                                provider_type="fwa",
                                plan_name="Verizon 5G Home",
                                speed_down=300,
                                speed_up=20,
                                monthly_price=price,
                            )
                        )
                if plans:
                    return plans
        except Exception as e:
            self.logger.debug(f"Verizon 5G Playwright parse failed: {e}")
        return None

    def published_plans(self, location: Location) -> list[Plan]:
        return [
            Plan(
                provider="Verizon 5G Home",
                provider_type="fwa",
                plan_name="Verizon LTE Home Internet",
                speed_down=85,
                speed_up=10,
                monthly_price=60.00,
            ),
            Plan(
                provider="Verizon 5G Home",
                provider_type="fwa",
                plan_name="Verizon 5G Home",
                speed_down=300,
                speed_up=20,
                monthly_price=60.00,
            ),
            Plan(
                provider="Verizon 5G Home",
                provider_type="fwa",
                plan_name="Verizon 5G Home Plus",
                speed_down=300,
                speed_up=20,
                monthly_price=80.00,
            ),
        ]
