"""Starlink pricing scraper."""

import re
from typing import Optional

from bs4 import BeautifulSoup

from broadband_pricing.models import Plan, Location
from broadband_pricing.providers.base import BaseProvider


class StarlinkProvider(BaseProvider):
    name = "starlink"
    provider_type = "starlink"

    PRICING_URL = "https://www.starlink.com/residential"
    API_URL = "https://www.starlink.com/api/pricing"

    def scrape_plans(self, location: Location) -> Optional[list[Plan]]:
        """Try to scrape current Starlink pricing."""
        # Try the API first
        plans = self._try_api(location)
        if plans:
            return plans

        # Try scraping the residential page
        plans = self._try_web_scrape()
        if plans:
            return plans

        # Try with Playwright
        return self._try_playwright()

    def _try_api(self, location: Location) -> Optional[list[Plan]]:
        try:
            resp = self.session.post(
                self.API_URL,
                json={"postalCode": location.zip_code, "country": "US"},
            )
            if resp and resp.status_code == 200:
                data = resp.json()
                plans = []
                for plan_data in data.get("plans", []):
                    plans.append(
                        Plan(
                            provider="Starlink",
                            provider_type="starlink",
                            plan_name=plan_data.get("name", "Standard"),
                            speed_down=plan_data.get("downloadSpeed", 100),
                            speed_up=plan_data.get("uploadSpeed", 10),
                            monthly_price=float(plan_data.get("price", 120)),
                        )
                    )
                if plans:
                    return plans
        except Exception as e:
            self.logger.debug(f"Starlink API failed: {e}")
        return None

    def _try_web_scrape(self) -> Optional[list[Plan]]:
        try:
            resp = self.session.get(self.PRICING_URL)
            if not resp:
                return None

            soup = BeautifulSoup(resp.text, "lxml")
            text = soup.get_text()

            # Look for pricing patterns like $120/mo or $120/month
            prices = re.findall(r"\$(\d+(?:\.\d{2})?)\s*/\s*mo", text)
            if prices:
                self.logger.info(f"Found Starlink prices: {prices}")

            # Look for plan names and prices in structured elements
            plan_cards = soup.find_all(
                ["div", "section"],
                class_=re.compile(r"plan|pricing|card|tier", re.I),
            )
            if plan_cards:
                plans = []
                for card in plan_cards:
                    card_text = card.get_text()
                    price_match = re.search(r"\$(\d+(?:\.\d{2})?)", card_text)
                    if price_match:
                        price = float(price_match.group(1))
                        name = "Standard" if price < 150 else "Priority"
                        speed = 100 if price < 150 else 220
                        plans.append(
                            Plan(
                                provider="Starlink",
                                provider_type="starlink",
                                plan_name=f"Starlink {name}",
                                speed_down=speed,
                                speed_up=10 if price < 150 else 25,
                                monthly_price=price,
                            )
                        )
                if plans:
                    return plans

        except Exception as e:
            self.logger.debug(f"Starlink web scrape failed: {e}")
        return None

    def _try_playwright(self) -> Optional[list[Plan]]:
        html = self.session.get_with_playwright(self.PRICING_URL)
        if not html:
            return None

        try:
            soup = BeautifulSoup(html, "lxml")
            prices = re.findall(r"\$(\d+(?:\.\d{2})?)\s*/\s*mo", soup.get_text())
            if prices:
                plans = []
                for i, price_str in enumerate(prices[:3]):
                    price = float(price_str)
                    if price < 80 or price > 500:
                        continue
                    name = "Standard" if price < 150 else "Priority"
                    plans.append(
                        Plan(
                            provider="Starlink",
                            provider_type="starlink",
                            plan_name=f"Starlink {name}",
                            speed_down=100 if price < 150 else 220,
                            speed_up=10 if price < 150 else 25,
                            monthly_price=price,
                        )
                    )
                if plans:
                    return plans
        except Exception as e:
            self.logger.debug(f"Starlink Playwright parse failed: {e}")
        return None

    def published_plans(self, location: Location) -> list[Plan]:
        return [
            Plan(
                provider="Starlink",
                provider_type="starlink",
                plan_name="Starlink Standard",
                speed_down=100,
                speed_up=10,
                monthly_price=120.00,
            ),
            Plan(
                provider="Starlink",
                provider_type="starlink",
                plan_name="Starlink Priority",
                speed_down=220,
                speed_up=25,
                monthly_price=200.00,
            ),
        ]
