"""T-Mobile Home Internet (FWA) pricing scraper."""

import re
from typing import Optional

from bs4 import BeautifulSoup

from broadband_pricing.models import Plan, Location
from broadband_pricing.providers.base import BaseProvider
from broadband_pricing.http_client import get_api_headers


class TMobileHomeProvider(BaseProvider):
    name = "tmobile_home"
    provider_type = "fwa"

    ISP_URL = "https://www.t-mobile.com/home-internet"
    API_URL = "https://www.t-mobile.com/isp/api/availability"

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
            headers = get_api_headers(referer="https://www.t-mobile.com/home-internet")
            resp = self.session.post(
                self.API_URL,
                headers=headers,
                json={
                    "address": location.address,
                    "city": location.city,
                    "state": location.state,
                    "zipCode": location.zip_code,
                },
            )
            if resp and resp.status_code == 200:
                data = resp.json()
                plans = []
                for product in data.get("plans", data.get("products", [])):
                    name = product.get("name", "T-Mobile Home Internet")
                    price = product.get("price", product.get("monthlyPrice", 0))
                    speed = product.get("downloadSpeed", 245)
                    if price:
                        plans.append(
                            Plan(
                                provider="T-Mobile Home Internet",
                                provider_type="fwa",
                                plan_name=name,
                                speed_down=int(speed),
                                speed_up=int(product.get("uploadSpeed", 33)),
                                monthly_price=float(price),
                            )
                        )
                if plans:
                    return plans
        except Exception as e:
            self.logger.debug(f"T-Mobile API failed: {e}")
        return None

    def _try_web_scrape(self) -> Optional[list[Plan]]:
        try:
            resp = self.session.get(self.ISP_URL)
            if not resp:
                resp = self.session.get_with_cloudscraper(self.ISP_URL)
            if not resp:
                return None

            soup = BeautifulSoup(resp.text, "lxml")
            text = soup.get_text(separator=" ")

            # Look for the price
            price_matches = re.findall(r"\$(\d+(?:\.\d{2})?)\s*/\s*mo", text)
            plans = []
            seen_prices = set()
            for pm in price_matches:
                price = float(pm)
                if 30 <= price <= 100 and price not in seen_prices:
                    seen_prices.add(price)
                    plans.append(
                        Plan(
                            provider="T-Mobile Home Internet",
                            provider_type="fwa",
                            plan_name="T-Mobile 5G Home Internet"
                            if price <= 55
                            else "T-Mobile All-In Pricing",
                            speed_down=245,
                            speed_up=33,
                            monthly_price=price,
                        )
                    )
            if plans:
                return plans
        except Exception as e:
            self.logger.debug(f"T-Mobile web scrape failed: {e}")
        return None

    def _try_playwright(self) -> Optional[list[Plan]]:
        html = self.session.get_with_playwright(self.ISP_URL)
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
                    if 30 <= price <= 100:
                        plans.append(
                            Plan(
                                provider="T-Mobile Home Internet",
                                provider_type="fwa",
                                plan_name="T-Mobile 5G Home Internet",
                                speed_down=245,
                                speed_up=33,
                                monthly_price=price,
                            )
                        )
                if plans:
                    return plans
        except Exception as e:
            self.logger.debug(f"T-Mobile Playwright parse failed: {e}")
        return None

    def published_plans(self, location: Location) -> list[Plan]:
        return [
            Plan(
                provider="T-Mobile Home Internet",
                provider_type="fwa",
                plan_name="T-Mobile 5G Home Internet",
                speed_down=245,
                speed_up=33,
                monthly_price=50.00,
            ),
            Plan(
                provider="T-Mobile Home Internet",
                provider_type="fwa",
                plan_name="T-Mobile All-In Pricing",
                speed_down=245,
                speed_up=33,
                monthly_price=55.00,
            ),
        ]
