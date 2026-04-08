"""AT&T Internet Air (FWA) pricing scraper."""

import re
from typing import Optional

from bs4 import BeautifulSoup

from broadband_pricing.models import Plan, Location
from broadband_pricing.providers.base import BaseProvider
from broadband_pricing.http_client import get_api_headers


class AttAirProvider(BaseProvider):
    name = "att_air"
    provider_type = "fwa"

    AIR_URL = "https://www.att.com/internet/internet-air/"
    API_URL = "https://www.att.com/services/shop/model/global-ecom/json/offer-air"

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
            headers = get_api_headers(referer="https://www.att.com/internet/internet-air/")
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
                for offer in data.get("offers", data.get("plans", [])):
                    name = offer.get("name", "AT&T Internet Air")
                    price = offer.get("price", offer.get("monthlyPrice", 0))
                    speed = offer.get("downloadSpeed", 120)
                    if price:
                        plans.append(
                            Plan(
                                provider="AT&T Internet Air",
                                provider_type="fwa",
                                plan_name=name,
                                speed_down=int(speed),
                                speed_up=int(offer.get("uploadSpeed", 10)),
                                monthly_price=float(price),
                            )
                        )
                if plans:
                    return plans
        except Exception as e:
            self.logger.debug(f"AT&T Air API failed: {e}")
        return None

    def _try_web_scrape(self) -> Optional[list[Plan]]:
        try:
            resp = self.session.get(self.AIR_URL)
            if not resp:
                resp = self.session.get_with_cloudscraper(self.AIR_URL)
            if not resp:
                return None

            soup = BeautifulSoup(resp.text, "lxml")
            text = soup.get_text(separator=" ")

            price_matches = re.findall(r"\$(\d+(?:\.\d{2})?)\s*/\s*mo", text)
            plans = []
            seen_prices = set()
            for pm in price_matches:
                price = float(pm)
                if 30 <= price <= 80 and price not in seen_prices:
                    seen_prices.add(price)
                    plans.append(
                        Plan(
                            provider="AT&T Internet Air",
                            provider_type="fwa",
                            plan_name="AT&T Internet Air",
                            speed_down=120,
                            speed_up=10,
                            monthly_price=price,
                        )
                    )
            if plans:
                return plans
        except Exception as e:
            self.logger.debug(f"AT&T Air web scrape failed: {e}")
        return None

    def _try_playwright(self) -> Optional[list[Plan]]:
        html = self.session.get_with_playwright(self.AIR_URL)
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
                    if 30 <= price <= 80:
                        plans.append(
                            Plan(
                                provider="AT&T Internet Air",
                                provider_type="fwa",
                                plan_name="AT&T Internet Air",
                                speed_down=120,
                                speed_up=10,
                                monthly_price=price,
                            )
                        )
                if plans:
                    return plans
        except Exception as e:
            self.logger.debug(f"AT&T Air Playwright parse failed: {e}")
        return None

    def published_plans(self, location: Location) -> list[Plan]:
        return [
            Plan(
                provider="AT&T Internet Air",
                provider_type="fwa",
                plan_name="AT&T Internet Air",
                speed_down=120,
                speed_up=10,
                monthly_price=55.00,
            ),
            Plan(
                provider="AT&T Internet Air",
                provider_type="fwa",
                plan_name="AT&T Internet Air (w/ wireless)",
                speed_down=120,
                speed_up=10,
                monthly_price=45.00,
            ),
        ]
