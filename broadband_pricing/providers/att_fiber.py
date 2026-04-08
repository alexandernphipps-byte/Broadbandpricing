"""AT&T Fiber pricing scraper."""

import re
from typing import Optional

from bs4 import BeautifulSoup

from broadband_pricing.models import Plan, Location
from broadband_pricing.providers.base import BaseProvider
from broadband_pricing.http_client import get_api_headers


class AttFiberProvider(BaseProvider):
    name = "att_fiber"
    provider_type = "ilec_fiber"

    INTERNET_URL = "https://www.att.com/internet/fiber/"
    API_URL = "https://www.att.com/services/shop/model/global-ecom/json/offer-702.json"
    AVAILABILITY_URL = "https://www.att.com/services/shop/model/global-ecom/json/addressSearch"

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
            headers = get_api_headers(referer="https://www.att.com/internet/")

            # Try the offers API
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
                offers = data.get("offers", data.get("plans", data.get("items", [])))
                for offer in offers:
                    name = offer.get("offerName", offer.get("name", ""))
                    price = offer.get("price", offer.get("monthlyPrice", 0))
                    speed = offer.get("downloadSpeed", offer.get("speed", 0))
                    if "fiber" in name.lower() or "internet" in name.lower():
                        if price and speed:
                            plans.append(
                                Plan(
                                    provider="AT&T Fiber",
                                    provider_type="ilec_fiber",
                                    plan_name=name,
                                    speed_down=int(speed),
                                    speed_up=int(offer.get("uploadSpeed", speed)),
                                    monthly_price=float(price),
                                )
                            )
                if plans:
                    return plans
        except Exception as e:
            self.logger.debug(f"AT&T Fiber API failed: {e}")
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
                speed_match = re.search(r"(\d+)\s*(?:Mbps|Gbps|Gig)", text, re.I)
                if price_match and speed_match:
                    price = float(price_match.group(1))
                    speed = int(speed_match.group(1))
                    speed_text = speed_match.group(0)
                    if "Gig" in speed_text or "Gbps" in speed_text:
                        if speed < 10:
                            speed *= 1000
                    if 30 <= price <= 300 and speed >= 100:
                        plans.append(
                            Plan(
                                provider="AT&T Fiber",
                                provider_type="ilec_fiber",
                                plan_name=f"AT&T Fiber {speed} Mbps",
                                speed_down=speed,
                                speed_up=speed,
                                monthly_price=price,
                            )
                        )
            if plans:
                return plans
        except Exception as e:
            self.logger.debug(f"AT&T Fiber web scrape failed: {e}")
        return None

    def _try_playwright(self) -> Optional[list[Plan]]:
        html = self.session.get_with_playwright(
            self.INTERNET_URL, wait_selector="[class*='plan'], [class*='offer']"
        )
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
                    if 30 <= price <= 300:
                        plans.append(
                            Plan(
                                provider="AT&T Fiber",
                                provider_type="ilec_fiber",
                                plan_name=f"AT&T Fiber ${price}",
                                speed_down=300,
                                speed_up=300,
                                monthly_price=price,
                            )
                        )
                if plans:
                    return plans
        except Exception as e:
            self.logger.debug(f"AT&T Fiber Playwright parse failed: {e}")
        return None

    def published_plans(self, location: Location) -> list[Plan]:
        return [
            Plan(
                provider="AT&T Fiber",
                provider_type="ilec_fiber",
                plan_name="AT&T Fiber 300",
                speed_down=300,
                speed_up=300,
                monthly_price=55.00,
            ),
            Plan(
                provider="AT&T Fiber",
                provider_type="ilec_fiber",
                plan_name="AT&T Fiber 500",
                speed_down=500,
                speed_up=500,
                monthly_price=65.00,
            ),
            Plan(
                provider="AT&T Fiber",
                provider_type="ilec_fiber",
                plan_name="AT&T Fiber 1 Gig",
                speed_down=1000,
                speed_up=1000,
                monthly_price=80.00,
            ),
            Plan(
                provider="AT&T Fiber",
                provider_type="ilec_fiber",
                plan_name="AT&T Fiber 2 Gig",
                speed_down=2000,
                speed_up=2000,
                monthly_price=110.00,
            ),
            Plan(
                provider="AT&T Fiber",
                provider_type="ilec_fiber",
                plan_name="AT&T Fiber 5 Gig",
                speed_down=5000,
                speed_up=5000,
                monthly_price=180.00,
            ),
        ]
