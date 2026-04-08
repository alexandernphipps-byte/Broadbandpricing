"""Verizon Fios pricing scraper."""

import re
from typing import Optional

from bs4 import BeautifulSoup

from broadband_pricing.models import Plan, Location
from broadband_pricing.providers.base import BaseProvider
from broadband_pricing.http_client import get_api_headers


class VerizonFiosProvider(BaseProvider):
    name = "verizon_fios"
    provider_type = "ilec_fiber"

    INTERNET_URL = "https://www.verizon.com/home/fios-fastest-internet/"
    API_URL = "https://www.verizon.com/inhome/api/product/fios/plans"

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
            headers = get_api_headers(referer="https://www.verizon.com/home/fios-fastest-internet/")
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
                    speed = product.get("downloadSpeed", product.get("speed", 0))
                    if name and price and speed:
                        plans.append(
                            Plan(
                                provider="Verizon Fios",
                                provider_type="ilec_fiber",
                                plan_name=name,
                                speed_down=int(speed),
                                speed_up=int(product.get("uploadSpeed", speed)),
                                monthly_price=float(price),
                            )
                        )
                if plans:
                    return plans
        except Exception as e:
            self.logger.debug(f"Verizon Fios API failed: {e}")
        return None

    def _try_web_scrape(self) -> Optional[list[Plan]]:
        try:
            resp = self.session.get(self.INTERNET_URL)
            if not resp:
                resp = self.session.get_with_cloudscraper(self.INTERNET_URL)
            if not resp:
                return None

            soup = BeautifulSoup(resp.text, "lxml")
            plan_cards = soup.find_all(
                ["div", "li", "section"],
                class_=re.compile(r"plan|offer|package|card|tier", re.I),
            )
            plans = []
            for card in plan_cards:
                text = card.get_text(separator=" ")
                price_match = re.search(r"\$(\d+(?:\.\d{2})?)\s*/\s*mo", text)
                speed_match = re.search(r"(\d+)\s*(?:Mbps|Gbps)", text, re.I)
                if price_match and speed_match:
                    price = float(price_match.group(1))
                    speed = int(speed_match.group(1))
                    if "Gbps" in speed_match.group(0):
                        speed *= 1000
                    if 30 <= price <= 200 and speed >= 100:
                        plans.append(
                            Plan(
                                provider="Verizon Fios",
                                provider_type="ilec_fiber",
                                plan_name=f"Fios {speed} Mbps",
                                speed_down=speed,
                                speed_up=speed,
                                monthly_price=price,
                            )
                        )
            if plans:
                return plans
        except Exception as e:
            self.logger.debug(f"Verizon Fios web scrape failed: {e}")
        return None

    def _try_playwright(self) -> Optional[list[Plan]]:
        html = self.session.get_with_playwright(self.INTERNET_URL)
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
                    if 30 <= price <= 200:
                        plans.append(
                            Plan(
                                provider="Verizon Fios",
                                provider_type="ilec_fiber",
                                plan_name=f"Fios ${price}",
                                speed_down=300,
                                speed_up=300,
                                monthly_price=price,
                            )
                        )
                if plans:
                    return plans
        except Exception as e:
            self.logger.debug(f"Verizon Fios Playwright parse failed: {e}")
        return None

    def published_plans(self, location: Location) -> list[Plan]:
        return [
            Plan(
                provider="Verizon Fios",
                provider_type="ilec_fiber",
                plan_name="Fios 300 Mbps",
                speed_down=300,
                speed_up=300,
                monthly_price=49.99,
            ),
            Plan(
                provider="Verizon Fios",
                provider_type="ilec_fiber",
                plan_name="Fios 500 Mbps",
                speed_down=500,
                speed_up=500,
                monthly_price=69.99,
            ),
            Plan(
                provider="Verizon Fios",
                provider_type="ilec_fiber",
                plan_name="Fios 1 Gig",
                speed_down=1000,
                speed_up=1000,
                monthly_price=89.99,
            ),
            Plan(
                provider="Verizon Fios",
                provider_type="ilec_fiber",
                plan_name="Fios 2 Gig",
                speed_down=2000,
                speed_up=2000,
                monthly_price=119.99,
            ),
        ]
