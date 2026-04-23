#!/usr/bin/env python3
"""FCC Broadband Data Collection (BDC) Provider Search.

Uses the FCC BDC public API at bdc.fcc.gov to download the latest availability
data, parse it, and let users search by provider to see homes passed per state.

Required env vars (generate credentials at broadbandmap.fcc.gov → your username
→ "Manage API Access" → "Generate"):

    FCC_USERNAME  – your FCC User Registration username (email address)
    FCC_API_KEY   – your 44-character API token

Run:
    FCC_USERNAME=you@example.com FCC_API_KEY=yourtoken python fcc_search.py
"""

import csv
import io
import os
import threading
from datetime import datetime

import requests
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

BDC_BASE = "https://bdc.fcc.gov/api/public"
_USERNAME = os.environ.get("FCC_USERNAME", "")
_API_KEY  = os.environ.get("FCC_API_KEY", "")

# ── In-memory cache ────────────────────────────────────────────────────────
_lock = threading.Lock()
_cache: dict = {
    "status":      "idle",   # idle | loading | ready | error
    "message":     "",
    "as_of_date":  None,
    "providers":   [],       # [{provider_id, brand_name, holding_company}]
    "by_provider": {},       # provider_id -> {brand_name, states: [...]}
}


# ── FCC BDC API helpers ────────────────────────────────────────────────────

def _headers() -> dict:
    h: dict = {"Accept": "application/json"}
    if _USERNAME:
        h["username"] = _USERNAME
    if _API_KEY:
        h["hash_value"] = _API_KEY
    return h


def _get(path: str, params=None):
    r = requests.get(f"{BDC_BASE}{path}", params=params, headers=_headers(), timeout=30)
    r.raise_for_status()
    return r.json()


def _download(url: str) -> bytes:
    r = requests.get(url, headers=_headers(), timeout=180)
    r.raise_for_status()
    return r.content


# ── Background data loader ─────────────────────────────────────────────────

def _set_status(status: str, message: str = "") -> None:
    with _lock:
        _cache["status"]  = status
        _cache["message"] = message


def load_bdc_data() -> None:
    """Download the latest BDC state-level summary file and cache parsed data."""
    try:
        _set_status("loading", "Fetching available filing dates…")

        dates_raw = _get("/map/listAsOfDates")
        dates = dates_raw.get("data", dates_raw) if isinstance(dates_raw, dict) else dates_raw
        if not dates:
            raise RuntimeError("No filing dates returned by the API.")

        as_of_date = _pick_latest_date(dates)
        _set_status("loading", f"Listing data files for {as_of_date}…")

        files_raw = _get(f"/map/downloads/listAvailabilityData/{as_of_date}")
        files = files_raw.get("data", files_raw) if isinstance(files_raw, dict) else files_raw
        if not files:
            raise RuntimeError(f"No data files listed for filing date {as_of_date!r}.")

        target = _pick_summary_file(files)
        if not target:
            raise RuntimeError(
                f"Could not identify a state-level provider summary file. "
                f"Files available: {[f.get('file_name') or f.get('name') for f in files]}"
            )

        file_url = (
            target.get("file_url")
            or target.get("url")
            or target.get("download_url")
            or target.get("link")
        )
        if not file_url:
            raise RuntimeError(f"Selected file has no download URL: {target}")

        fname = target.get("file_name") or target.get("name") or "data"
        _set_status("loading", f"Downloading {fname}…")
        raw = _download(file_url)

        _set_status("loading", "Parsing CSV…")
        by_provider = _parse_csv(raw)

        if not by_provider:
            raise RuntimeError(
                "CSV parsed successfully but no provider rows were found. "
                "The file may have an unexpected format or different column names."
            )

        providers = sorted(
            [
                {
                    "provider_id":    pid,
                    "brand_name":     info["brand_name"],
                    "holding_company": info.get("holding_company", ""),
                }
                for pid, info in by_provider.items()
            ],
            key=lambda p: p["brand_name"].lower(),
        )

        with _lock:
            _cache["status"]      = "ready"
            _cache["message"]     = ""
            _cache["as_of_date"]  = str(as_of_date)
            _cache["providers"]   = providers
            _cache["by_provider"] = by_provider

    except Exception as exc:
        _set_status("error", str(exc))
        raise


def _pick_latest_date(dates: list):
    def _key(d):
        return str(d.get("as_of_date") or d.get("date") or d) if isinstance(d, dict) else str(d)

    ordered = sorted(dates, key=_key, reverse=True)
    top = ordered[0]
    return top.get("as_of_date") or top.get("date") or top if isinstance(top, dict) else top


def _pick_summary_file(files: list) -> dict | None:
    """Rank available files and return the most likely state × provider summary."""
    def _score(f: dict) -> int:
        name = (f.get("file_name") or f.get("name") or "").lower()
        s = 0
        if "state"        in name: s += 4
        if "provider"     in name: s += 3
        if "summary"      in name: s += 2
        if "availability" in name: s += 1
        if "national"     in name: s += 1
        return s

    ranked = sorted(files, key=_score, reverse=True)
    return ranked[0] if ranked else None


def _parse_csv(raw: bytes) -> dict:
    """Parse a BDC availability CSV into {provider_id: {brand_name, states: [...]}}."""
    text = raw.decode("utf-8", errors="replace")
    delim = "|" if text.count("|") > text.count(",") else ","
    reader = csv.DictReader(io.StringIO(text), delimiter=delim)

    by_provider: dict = {}

    for row in reader:
        r = {k.strip().lower().replace(" ", "_"): (v or "").strip() for k, v in row.items()}

        pid     = r.get("provider_id") or r.get("frn") or ""
        brand   = r.get("brand_name") or r.get("provider_name") or r.get("name") or pid
        holding = (
            r.get("holding_company_final_name")
            or r.get("holding_company_name")
            or r.get("holding_company")
            or ""
        )
        state_name = (
            r.get("state_name") or r.get("state") or r.get("geography_desc") or ""
        )
        state_abbr = (
            r.get("state_abbr") or r.get("state_code") or r.get("abbr") or ""
        )

        # Residential locations — try each known column name in priority order
        homes = _first_int(r, [
            "residential_units",
            "total_residential",
            "res_location_count",
            "homes_passed",
            "residential_high_speed_2_0",
            "location_count",
        ])
        biz = _first_int(r, [
            "business_units",
            "total_business",
            "biz_location_count",
            "business_passed",
            "business_high_speed_2_0",
        ])

        if not pid or not state_name:
            continue

        if pid not in by_provider:
            by_provider[pid] = {
                "brand_name":    brand,
                "holding_company": holding,
                "states":        [],
            }

        by_provider[pid]["states"].append({
            "state_name":      state_name,
            "state_abbr":      state_abbr,
            "homes_passed":    homes,
            "business_passed": biz,
        })

    for info in by_provider.values():
        info["states"].sort(key=lambda s: s["homes_passed"], reverse=True)

    return by_provider


def _first_int(row: dict, cols: list) -> int:
    for col in cols:
        val = row.get(col, "").replace(",", "").strip()
        if val:
            try:
                return int(float(val))
            except ValueError:
                continue
    return 0


# ── Flask routes ───────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("fcc_search.html")


@app.route("/api/status")
def api_status():
    with _lock:
        return jsonify({
            "status":     _cache["status"],
            "message":    _cache["message"],
            "as_of_date": _cache["as_of_date"],
        })


@app.route("/api/reload", methods=["POST"])
def api_reload():
    with _lock:
        if _cache["status"] == "loading":
            return jsonify({"error": "Already loading"}), 409
    threading.Thread(target=load_bdc_data, daemon=True).start()
    return jsonify({"ok": True})


@app.route("/api/providers")
def api_providers():
    with _lock:
        status = _cache["status"]
        if status != "ready":
            msg = _cache["message"]
            return jsonify({"error": f"Data not ready (status: {status}). {msg}"}), 503
        return jsonify({
            "providers":  _cache["providers"],
            "as_of_date": _cache["as_of_date"],
        })


@app.route("/api/homes-passed")
def api_homes_passed():
    provider_id = request.args.get("provider_id", "").strip()
    if not provider_id:
        return jsonify({"error": "provider_id is required"}), 400
    with _lock:
        if _cache["status"] != "ready":
            return jsonify({"error": "Data not ready"}), 503
        info       = _cache["by_provider"].get(provider_id)
        as_of_date = _cache["as_of_date"]
    if not info:
        return jsonify({"error": f"Provider '{provider_id}' not found in cache"}), 404
    return jsonify({"states": info["states"], "as_of_date": as_of_date})


# ── Entry point ────────────────────────────────────────────────────────────

def start():
    port  = int(os.environ.get("PORT", 5001))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    print(f"\n  FCC BDC Provider Search  →  http://localhost:{port}\n")
    if not _USERNAME:
        print("  WARNING: FCC_USERNAME not set – API calls will likely fail.\n")
    if not _API_KEY:
        print("  WARNING: FCC_API_KEY not set – API calls will likely fail.\n")
    threading.Thread(target=load_bdc_data, daemon=True).start()
    # host='0.0.0.0' required for cloud deployments (Railway, Render, etc.)
    app.run(host="0.0.0.0", port=port, debug=debug, use_reloader=False)


if __name__ == "__main__":
    start()
