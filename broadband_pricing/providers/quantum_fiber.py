"""Quantum Fiber (CenturyLink/Lumen) pricing scraper."""

import re
from typing import Optional

from bs4 import BeautifulSoup

from broadband_pricing.models import Plan, Location
from broadband_pricing.providers.base import BaseProvider
from broadband_pricing.http_client import get_api_headers


class QuantumFiberProvider(BaseProvider):
    name = "quantum_fiber"
    provider_type = "ilec_fiber"

    INTERNET_URL = "https://www.quantumfiber.com/internet"
    API_URL = "https://www.quantumfiber.com/api/plans"

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
            headers = get_api_headers(referer="https://www.quantumfiber.com/internet")
            resp = self.session.get(
                self.API_URL,
                headers=headers,
                params={"zip": location.zip_code},
            )
            if resp and resp.status_code == 200:
                data = resp.json()
                plans = []
                for product in data.get("plans", data.get("products", [])):
                    name = product.get("name", "")
                    price = product.get("price", product.get("monthlyPrice", 0))
                    speed = product.get("downloadSpeed", product.get("speed", 0))
                    if name and price and speed:
                        plans.append(
                            Plan(
                                provider="Quantum Fiber",
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
            self.logger.debug(f"Quantum Fiber API failed: {e}")
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
                class_=re.compile(r"plan|offer|package|card|tier|pricing", re.I),
            )
            plans = []
            for card in plan_cards:
                text = card.get_text(separator=" ")
                price_match = re.search(r"\$(\d+(?:\.\d{2})?)\s*/\s*mo", text)
                speed_match = re.search(r"(\d+)\s*(?:Mbps|Gbps|Gig)", text, re.I)
                if price_match and speed_match:
                    price = float(price_match.group(1))
                    speed = int(speed_match.group(1))
                    speed_text = speed_match.group(0)
                    if "Gig" in speed_text or "Gbps" in speed_text:
                        if speed < 10:
                            speed *= 1000
                    if 20 <= price <= 200 and speed >= 100:
                        plans.append(
                            Plan(
                                provider="Quantum Fiber",
                                provider_type="ilec_fiber",
                                plan_name=f"Quantum Fiber {speed} Mbps",
                                speed_down=speed,
                                speed_up=speed,
                                monthly_price=price,
                            )
                        )
            if plans:
                return plans
        except Exception as e:
            self.logger.debug(f"Quantum Fiber web scrape failed: {e}")
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
                    if 20 <= price <= 200:
                        plans.append(
                            Plan(
                                provider="Quantum Fiber",
                                provider_type="ilec_fiber",
                                plan_name=f"Quantum Fiber ${price}",
                                speed_down=500,
                                speed_up=500,
                                monthly_price=price,
                            )
                        )
                if plans:
                    return plans
        except Exception as e:
            self.logger.debug(f"Quantum Fiber Playwright parse failed: {e}")
        return None

    def published_plans(self, location: Location) -> list[Plan]:
        return [
            Plan(
                provider="Quantum Fiber",
                provider_type="ilec_fiber",
                plan_name="Quantum Fiber 200",
                speed_down=200,
                speed_up=200,
                monthly_price=30.00,
            ),
            Plan(
                provider="Quantum Fiber",
                provider_type="ilec_fiber",
                plan_name="Quantum Fiber 500",
                speed_down=500,
                speed_up=500,
                monthly_price=40.00,
            ),
            Plan(
                provider="Quantum Fiber",
                provider_type="ilec_fiber",
                plan_name="Quantum Fiber 940",
                speed_down=940,
                speed_up=940,
                monthly_price=50.00,
            ),
            Plan(
                provider="Quantum Fiber",
                provider_type="ilec_fiber",
                plan_name="Quantum Fiber 2 Gig",
                speed_down=2000,
                speed_up=2000,
                monthly_price=70.00,
            ),
            Plan(
                provider="Quantum Fiber",
                provider_type="ilec_fiber",
                plan_name="Quantum Fiber 8 Gig",
                speed_down=8000,
                speed_up=8000,
                monthly_price=150.00,
            ),
        ]
