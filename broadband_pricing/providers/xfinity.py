"""Xfinity (Comcast) pricing scraper."""

import re
from typing import Optional

from bs4 import BeautifulSoup

from broadband_pricing.models import Plan, Location
from broadband_pricing.providers.base import BaseProvider
from broadband_pricing.http_client import get_api_headers


class XfinityProvider(BaseProvider):
    name = "xfinity"
    provider_type = "cable"

    OFFERS_URL = "https://www.xfinity.com/learn/internet-service/internet"
    API_URL = "https://www.xfinity.com/api/product/internet/offers"
    SERVICEABILITY_URL = "https://www.xfinity.com/api/serviceability"

    def scrape_plans(self, location: Location) -> Optional[list[Plan]]:
        plans = self._try_api(location)
        if plans:
            return plans

        plans = self._try_web_scrape()
        if plans:
            return plans

        return self._try_playwright()

    def _try_api(self, location: Location) -> Optional[list[Plan]]:
        """Try Xfinity's internal API for plan offers."""
        try:
            headers = get_api_headers(referer="https://www.xfinity.com/learn/internet-service")

            # Try the offers API
            resp = self.session.post(
                self.API_URL,
                headers=headers,
                json={
                    "address": {
                        "streetAddress": location.address,
                        "city": location.city,
                        "state": location.state,
                        "zipCode": location.zip_code,
                    }
                },
            )
            if resp and resp.status_code == 200:
                data = resp.json()
                offers = data.get("offers", data.get("products", []))
                plans = []
                for offer in offers:
                    speed = offer.get("downloadSpeed", offer.get("speed", 0))
                    price = offer.get("price", offer.get("monthlyPrice", 0))
                    name = offer.get("name", offer.get("planName", ""))
                    if speed and price and name:
                        plans.append(
                            Plan(
                                provider="Xfinity",
                                provider_type="cable",
                                plan_name=name,
                                speed_down=int(speed),
                                speed_up=int(offer.get("uploadSpeed", speed // 10)),
                                monthly_price=float(price),
                                is_introductory=offer.get("isPromo", False),
                                regular_price=offer.get("regularPrice"),
                            )
                        )
                if plans:
                    return plans
        except Exception as e:
            self.logger.debug(f"Xfinity API failed: {e}")
        return None

    def _try_web_scrape(self) -> Optional[list[Plan]]:
        """Try scraping the Xfinity internet page."""
        try:
            resp = self.session.get(self.OFFERS_URL)
            if not resp:
                resp = self.session.get_with_cloudscraper(self.OFFERS_URL)
            if not resp:
                return None

            soup = BeautifulSoup(resp.text, "lxml")

            # Look for plan cards with pricing
            plan_elements = soup.find_all(
                ["div", "li", "article"],
                class_=re.compile(r"plan|offer|package|card|tier", re.I),
            )
            plans = []
            for elem in plan_elements:
                text = elem.get_text(separator=" ")
                price_match = re.search(r"\$(\d+(?:\.\d{2})?)\s*/\s*mo", text)
                speed_match = re.search(r"(\d+)\s*(?:Mbps|Gbps)", text, re.I)
                if price_match and speed_match:
                    price = float(price_match.group(1))
                    speed_str = speed_match.group(0)
                    speed = int(speed_match.group(1))
                    if "Gbps" in speed_str or "gbps" in speed_str:
                        speed *= 1000

                    if 20 <= price <= 200 and speed >= 25:
                        name_match = re.search(
                            r"(Connect(?:\s+More)?|Fast|Superfast|Gigabit(?:\s+Extra)?)",
                            text,
                            re.I,
                        )
                        name = name_match.group(1) if name_match else f"{speed} Mbps"
                        plans.append(
                            Plan(
                                provider="Xfinity",
                                provider_type="cable",
                                plan_name=f"Xfinity {name}",
                                speed_down=speed,
                                speed_up=max(speed // 10, 5),
                                monthly_price=price,
                                is_introductory=True,
                                intro_duration_months=12,
                            )
                        )
            if plans:
                return plans
        except Exception as e:
            self.logger.debug(f"Xfinity web scrape failed: {e}")
        return None

    def _try_playwright(self) -> Optional[list[Plan]]:
        """Use Playwright for JS-rendered content."""
        html = self.session.get_with_playwright(
            self.OFFERS_URL, wait_selector="[class*='plan'], [class*='offer']"
        )
        if not html:
            return None

        try:
            soup = BeautifulSoup(html, "lxml")
            text = soup.get_text()
            prices = re.findall(r"\$(\d+(?:\.\d{2})?)\s*/\s*mo", text)
            speeds = re.findall(r"(\d+)\s*(?:Mbps|Gbps)", text, re.I)
            if prices and speeds:
                plans = []
                for price_str, speed_str in zip(prices, speeds):
                    price = float(price_str)
                    speed = int(speed_str)
                    if 20 <= price <= 200 and speed >= 25:
                        plans.append(
                            Plan(
                                provider="Xfinity",
                                provider_type="cable",
                                plan_name=f"Xfinity {speed} Mbps",
                                speed_down=speed,
                                speed_up=max(speed // 10, 5),
                                monthly_price=price,
                                is_introductory=True,
                            )
                        )
                if plans:
                    return plans
        except Exception as e:
            self.logger.debug(f"Xfinity Playwright parse failed: {e}")
        return None

    def published_plans(self, location: Location) -> list[Plan]:
        return [
            Plan(
                provider="Xfinity",
                provider_type="cable",
                plan_name="Xfinity Connect",
                speed_down=75,
                speed_up=10,
                monthly_price=30.00,
                is_introductory=True,
                intro_duration_months=12,
                regular_price=50.00,
            ),
            Plan(
                provider="Xfinity",
                provider_type="cable",
                plan_name="Xfinity Connect More",
                speed_down=200,
                speed_up=10,
                monthly_price=35.00,
                is_introductory=True,
                intro_duration_months=12,
                regular_price=65.00,
            ),
            Plan(
                provider="Xfinity",
                provider_type="cable",
                plan_name="Xfinity Fast",
                speed_down=400,
                speed_up=10,
                monthly_price=55.00,
                is_introductory=True,
                intro_duration_months=12,
                regular_price=80.00,
            ),
            Plan(
                provider="Xfinity",
                provider_type="cable",
                plan_name="Xfinity Superfast",
                speed_down=800,
                speed_up=20,
                monthly_price=65.00,
                is_introductory=True,
                intro_duration_months=12,
                regular_price=90.00,
            ),
            Plan(
                provider="Xfinity",
                provider_type="cable",
                plan_name="Xfinity Gigabit",
                speed_down=1000,
                speed_up=35,
                monthly_price=75.00,
                is_introductory=True,
                intro_duration_months=12,
                regular_price=100.00,
            ),
            Plan(
                provider="Xfinity",
                provider_type="cable",
                plan_name="Xfinity Gigabit Extra",
                speed_down=1200,
                speed_up=35,
                monthly_price=80.00,
                is_introductory=True,
                intro_duration_months=12,
                regular_price=110.00,
            ),
        ]
