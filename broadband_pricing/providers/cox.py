"""Cox Communications pricing scraper."""

import re
from typing import Optional

from bs4 import BeautifulSoup

from broadband_pricing.models import Plan, Location
from broadband_pricing.providers.base import BaseProvider
from broadband_pricing.http_client import get_api_headers


class CoxProvider(BaseProvider):
    name = "cox"
    provider_type = "cable"

    INTERNET_URL = "https://www.cox.com/residential/internet.html"
    API_URL = "https://www.cox.com/api/residential/internet/plans"

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
            headers = get_api_headers(referer="https://www.cox.com/residential/internet.html")
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
                    price = product.get("price", product.get("monthlyRate", 0))
                    speed = product.get("downloadSpeed", 0)
                    if name and price and speed:
                        plans.append(
                            Plan(
                                provider="Cox",
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
            self.logger.debug(f"Cox API failed: {e}")
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
                    if 30 <= price <= 200 and speed >= 25:
                        plans.append(
                            Plan(
                                provider="Cox",
                                provider_type="cable",
                                plan_name=f"Cox {speed} Mbps",
                                speed_down=speed,
                                speed_up=max(speed // 10, 5),
                                monthly_price=price,
                            )
                        )
            if plans:
                return plans
        except Exception as e:
            self.logger.debug(f"Cox web scrape failed: {e}")
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
                    if 30 <= price <= 200 and speed >= 25:
                        plans.append(
                            Plan(
                                provider="Cox",
                                provider_type="cable",
                                plan_name=f"Cox {speed} Mbps",
                                speed_down=speed,
                                speed_up=max(speed // 10, 5),
                                monthly_price=price,
                            )
                        )
                if plans:
                    return plans
        except Exception as e:
            self.logger.debug(f"Cox Playwright parse failed: {e}")
        return None

    def published_plans(self, location: Location) -> list[Plan]:
        return [
            Plan(
                provider="Cox",
                provider_type="cable",
                plan_name="Cox Internet Essential 100",
                speed_down=100,
                speed_up=10,
                monthly_price=49.99,
            ),
            Plan(
                provider="Cox",
                provider_type="cable",
                plan_name="Cox Internet Preferred 250",
                speed_down=250,
                speed_up=10,
                monthly_price=69.99,
            ),
            Plan(
                provider="Cox",
                provider_type="cable",
                plan_name="Cox Internet Ultimate 500",
                speed_down=500,
                speed_up=10,
                monthly_price=89.99,
            ),
            Plan(
                provider="Cox",
                provider_type="cable",
                plan_name="Cox Gigablast",
                speed_down=1000,
                speed_up=35,
                monthly_price=109.99,
            ),
        ]
