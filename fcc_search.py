#!/usr/bin/env python3
"""FCC Broadband Provider Search - Flask web app.

Uses the FCC National Broadband Map public API to look up homes passed
(residential locations served) by provider across all states.

Credentials are read from environment variables:
    FCC_USERNAME  - FCC account username / email
    FCC_API_KEY   - FCC account API key (generate at broadbandmap.fcc.gov)

Run:
    FCC_USERNAME=you@example.com FCC_API_KEY=yourkey python fcc_search.py
"""

import os
import requests
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

FCC_BASE = "https://broadbandmap.fcc.gov/api/public"
_USERNAME = os.environ.get("FCC_USERNAME", "")
_API_KEY = os.environ.get("FCC_API_KEY", "")


def _fcc_headers() -> dict:
    """Build request headers. FCC uses custom username/x-api-key headers, not Basic Auth."""
    headers = {
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (compatible; BroadbandPricingApp/1.0)",
    }
    if _USERNAME:
        headers["username"] = _USERNAME
    if _API_KEY:
        headers["x-api-key"] = _API_KEY
    return headers


def _fcc_get(path: str, params: dict | None = None):
    url = f"{FCC_BASE}{path}"
    resp = requests.get(
        url,
        params=params,
        headers=_fcc_headers(),
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# Page routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("fcc_search.html")


# ---------------------------------------------------------------------------
# API proxy routes (keep credentials server-side)
# ---------------------------------------------------------------------------

@app.route("/api/status")
def api_status():
    """Return credential/config status so the UI can surface actionable errors."""
    return jsonify({
        "has_username": bool(_USERNAME),
        "has_api_key": bool(_API_KEY),
    })


@app.route("/api/providers")
def api_providers():
    """Return all providers that have filed availability data with the FCC."""
    if not _USERNAME or not _API_KEY:
        return jsonify({"error": "FCC credentials are not configured. Set FCC_USERNAME and FCC_API_KEY environment variables (in Railway: Variables tab)."}), 503
    try:
        data = _fcc_get("/map/listAvailabilityProviders")
        # Normalise: the API may wrap the list in a 'data' key
        providers = data.get("data", data) if isinstance(data, dict) else data
        # Sort by name for easy browsing
        if isinstance(providers, list):
            providers.sort(key=lambda p: (p.get("brand_name") or p.get("name") or "").lower())
        return jsonify({"providers": providers})
    except requests.HTTPError as exc:
        status = exc.response.status_code
        detail = exc.response.text[:200]
        if status == 403:
            return jsonify({"error": f"FCC API access denied (403). Your credentials may be incorrect, or this server's IP may need to be registered with the FCC. Detail: {detail}"}), 502
        return jsonify({"error": f"FCC API returned {status}: {detail}"}), 502
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/homes-passed")
def api_homes_passed():
    """Return homes-passed counts by state for a given provider_id."""
    provider_id = request.args.get("provider_id", "").strip()
    if not provider_id:
        return jsonify({"error": "provider_id parameter is required"}), 400

    try:
        data = _fcc_get(
            "/map/availability/summary",
            {
                "provider_id": provider_id,
                "geo_type": "state",
            },
        )
        rows = data.get("data", data) if isinstance(data, dict) else data
        states = _normalise_state_rows(rows)
        return jsonify({"states": states})
    except requests.HTTPError as exc:
        return jsonify({"error": f"FCC API returned {exc.response.status_code}: {exc.response.text[:200]}"}), 502
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


def _normalise_state_rows(rows):
    """Map FCC response fields to a consistent shape for the UI."""
    result = []
    for row in rows or []:
        result.append({
            "state_name": (
                row.get("state_name")
                or row.get("geo_name")
                or row.get("name")
                or row.get("state")
                or "Unknown"
            ),
            "state_abbr": (
                row.get("state_abbr")
                or row.get("geo_abbr")
                or row.get("abbr")
                or ""
            ),
            # Residential locations = homes passed
            "homes_passed": int(
                row.get("residential_units")
                or row.get("total_residential")
                or row.get("homes_passed")
                or row.get("total_units")
                or row.get("location_count")
                or 0
            ),
            "business_passed": int(
                row.get("business_units")
                or row.get("total_business")
                or row.get("business_passed")
                or 0
            ),
        })
    result.sort(key=lambda r: r["homes_passed"], reverse=True)
    return result


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"
    print(f"\n  FCC Broadband Search running at http://localhost:{port}\n")
    if not _USERNAME or not _API_KEY:
        missing = [v for v, val in [("FCC_USERNAME", _USERNAME), ("FCC_API_KEY", _API_KEY)] if not val]
        print(f"  WARNING: {', '.join(missing)} not set — FCC API calls will fail.\n")
        print("  Set them as environment variables (or in Railway's Variables tab).\n")
    app.run(debug=debug, port=port)
