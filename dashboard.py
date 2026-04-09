#!/usr/bin/env python3
"""Interactive web dashboard for broadband pricing data."""

import json
from collections import defaultdict
from datetime import datetime

from flask import Flask, render_template, jsonify, request

from broadband_pricing.config import LOCATIONS, PROVIDER_NAMES, PROVIDER_TYPE_NAMES
from broadband_pricing.database import init_db, get_latest_pricing, get_pricing_history, get_price_changes, get_all_check_dates, store_plans
from broadband_pricing.providers import get_provider

app = Flask(__name__)


def speed_label(speed_down):
    if speed_down >= 1000:
        gig = speed_down / 1000
        return f"{int(gig)} Gig" if gig == int(gig) else f"{gig:.1f} Gig"
    return f"{speed_down} Mbps"


def get_dashboard_data():
    """Build all data needed for the dashboard."""
    records = get_latest_pricing()
    if not records:
        return None

    # Summary stats
    cities = sorted(set(r["city"] for r in records))
    providers = sorted(set(r["provider"] for r in records))
    cheapest = min(records, key=lambda r: r["monthly_price"])
    priciest = max(records, key=lambda r: r["monthly_price"])

    # Group by city
    by_city = defaultdict(list)
    for r in records:
        by_city[f"{r['city']}, {r['state']}"].append(r)

    # Enrich records with speed labels
    for r in records:
        r["speed_down_label"] = speed_label(r["speed_down"])
        r["speed_up_label"] = speed_label(r["speed_up"])
        r["provider_type_label"] = PROVIDER_TYPE_NAMES.get(r["provider_type"], r["provider_type"])

    # Comparison data: cheapest per type per city
    type_order = ["cable", "ilec_fiber", "starlink", "fwa"]
    comparison = {}
    for city_name in sorted(by_city.keys()):
        comparison[city_name] = {}
        for ptype in type_order:
            matches = [r for r in by_city[city_name] if r["provider_type"] == ptype]
            if matches:
                best = min(matches, key=lambda r: r["monthly_price"])
                comparison[city_name][ptype] = {
                    "price": best["monthly_price"],
                    "speed": speed_label(best["speed_down"]),
                    "provider": best["provider"],
                    "plan": best["plan_name"],
                }

    # Speed tier comparison
    speed_tiers = [
        ("Basic (< 150 Mbps)", 0, 150),
        ("Mid (150-500 Mbps)", 150, 500),
        ("Fast (500-1 Gbps)", 500, 1100),
        ("Gigabit+ (1+ Gbps)", 1100, 100000),
    ]
    tier_data = {}
    for tier_name, min_s, max_s in speed_tiers:
        tier_data[tier_name] = {}
        for ptype in type_order:
            matches = [r for r in records if r["provider_type"] == ptype and min_s <= r["speed_down"] < max_s]
            if matches:
                best = min(matches, key=lambda r: r["monthly_price"])
                tier_data[tier_name][ptype] = best["monthly_price"]

    # Chart data: cheapest by city for each type
    chart_cities = sorted(by_city.keys())
    chart_series = {}
    for ptype in type_order:
        prices = []
        for city_name in chart_cities:
            matches = [r for r in by_city[city_name] if r["provider_type"] == ptype]
            if matches:
                prices.append(min(r["monthly_price"] for r in matches))
            else:
                prices.append(None)
        chart_series[ptype] = prices

    return {
        "records": records,
        "cities": cities,
        "providers": providers,
        "cheapest": cheapest,
        "priciest": priciest,
        "check_date": records[0]["check_date"],
        "total_plans": len(records),
        "by_city": {k: sorted(v, key=lambda r: (r["provider_type"], r["speed_down"])) for k, v in by_city.items()},
        "comparison": comparison,
        "tier_data": tier_data,
        "chart_cities": [c.split(",")[0] for c in chart_cities],
        "chart_series": chart_series,
        "type_order": type_order,
        "check_dates": get_all_check_dates(),
    }


@app.route("/")
def dashboard():
    init_db()
    data = get_dashboard_data()
    if not data:
        return render_template("dashboard.html", data=None)
    return render_template("dashboard.html", data=data, data_json=json.dumps(data, default=str))


@app.route("/api/check", methods=["POST"])
def run_check():
    """Run a price check via the web UI."""
    init_db()
    total_plans = 0
    total_providers = 0
    errors = []

    for location in LOCATIONS:
        for ptype, provider_key in location.providers.items():
            try:
                provider = get_provider(provider_key)
                source = "published"
                try:
                    plans = provider.scrape_plans(location)
                    if plans:
                        source = "scraped"
                except Exception:
                    plans = None
                if not plans:
                    plans = provider.published_plans(location)
                if plans:
                    store_plans(location, plans, source=source)
                    total_plans += len(plans)
                    total_providers += 1
            except Exception as e:
                errors.append(str(e))

    return jsonify({
        "status": "success",
        "plans": total_plans,
        "providers": total_providers,
        "errors": len(errors),
    })


@app.route("/api/data")
def get_data():
    """Return pricing data as JSON."""
    init_db()
    city = request.args.get("city")
    records = get_latest_pricing(city)
    return jsonify(records)


if __name__ == "__main__":
    init_db()
    print("\n  Broadband Pricing Dashboard")
    print("  Open your browser to: http://127.0.0.1:5000\n")
    app.run(debug=True, host="127.0.0.1", port=5000)
