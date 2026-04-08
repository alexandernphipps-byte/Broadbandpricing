"""Spectrum (Charter) pricing scraper."""

import re
from typing import Optional

from bs4 import BeautifulSoup

from broadband_pricing.models import Plan, Location
from broadband_pricing.providers.base import BaseProvider
from broadband_pricing.http_client import get_api_headers


class SpectrumProvider(BaseProvider):
    name = "spectrum"
    provider_type = "cable"

    INTERNET_URL = "https://www.spectrum.com/internet"
    API_URL = "https://www.spectrum.com/services/api/product/internet"

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
            headers = get_api_headers(referer="https://www.spectrum.com/internet")
            resp = self.session.post(
                self.API_URL,
                headers=headers,
                json={
                    "address": location.address,
                    "city": location.city,
                    "state": location.state,
                    "zip": location.zip_code,
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
                                provider="Spectrum",
                                provider_type="cable",
                                plan_name=name,
                                speed_down=int(speed),
                                speed_up=int(product.get("uploadSpeed", speed // 10)),
                                monthly_price=float(price),
                            )
                        )
                if plans:
                    return plans
        except Exception as e:
            self.logger.debug(f"Spectrum API failed: {e}")
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
                class_=re.compile(r"plan|package|offer|card|tier", re.I),
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
                    if 30 <= price <= 200 and speed >= 50:
                        name_match = re.search(r"(Internet(?:\s+\w+)?|Gig)", text, re.I)
                        name = name_match.group(1) if name_match else f"{speed} Mbps"
                        plans.append(
                            Plan(
                                provider="Spectrum",
                                provider_type="cable",
                                plan_name=f"Spectrum {name}",
                                speed_down=speed,
                                speed_up=max(speed // 10, 10),
                                monthly_price=price,
                            )
                        )
            if plans:
                return plans
        except Exception as e:
            self.logger.debug(f"Spectrum web scrape failed: {e}")
        return None

    def _try_playwright(self) -> Optional[list[Plan]]:
        html = self.session.get_with_playwright(self.INTERNET_URL)
        if not html:
            return None
        try:
            soup = BeautifulSoup(html, "lxml")
            text = soup.get_text()
            prices = re.findall(r"\$(\d+(?:\.\d{2})?)\s*/\s*mo", text)
            speeds = re.findall(r"(\d+)\s*(?:Mbps|Gbps)", text, re.I)
            if prices and speeds:
                plans = []
                for p, s in zip(prices, speeds):
                    price = float(p)
                    speed = int(s)
                    if 30 <= price <= 200 and speed >= 50:
                        plans.append(
                            Plan(
                                provider="Spectrum",
                                provider_type="cable",
                                plan_name=f"Spectrum {speed} Mbps",
                                speed_down=speed,
                                speed_up=max(speed // 10, 10),
                                monthly_price=price,
                            )
                        )
                if plans:
                    return plans
        except Exception as e:
            self.logger.debug(f"Spectrum Playwright parse failed: {e}")
        return None

    def published_plans(self, location: Location) -> list[Plan]:
        return [
            Plan(
                provider="Spectrum",
                provider_type="cable",
                plan_name="Spectrum Internet",
                speed_down=300,
                speed_up=10,
                monthly_price=49.99,
            ),
            Plan(
                provider="Spectrum",
                provider_type="cable",
                plan_name="Spectrum Internet Ultra",
                speed_down=500,
                speed_up=20,
                monthly_price=69.99,
            ),
            Plan(
                provider="Spectrum",
                provider_type="cable",
                plan_name="Spectrum Internet Gig",
                speed_down=1000,
                speed_up=35,
                monthly_price=89.99,
            ),
        ]
