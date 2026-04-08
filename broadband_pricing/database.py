"""SQLite database for storing historical pricing data."""

import os
import sqlite3
from datetime import datetime, date
from typing import Optional

from broadband_pricing.config import DB_PATH, DB_DIR
from broadband_pricing.models import Plan, PricingRecord, Location


def get_connection() -> sqlite3.Connection:
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """Create tables if they don't exist."""
    conn = get_connection()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS pricing_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            check_date TEXT NOT NULL,
            city TEXT NOT NULL,
            state TEXT NOT NULL,
            address TEXT NOT NULL,
            zip_code TEXT NOT NULL,
            provider TEXT NOT NULL,
            provider_type TEXT NOT NULL,
            plan_name TEXT NOT NULL,
            speed_down INTEGER NOT NULL,
            speed_up INTEGER NOT NULL,
            monthly_price REAL NOT NULL,
            is_introductory INTEGER DEFAULT 0,
            intro_duration_months INTEGER DEFAULT 0,
            regular_price REAL,
            source TEXT NOT NULL DEFAULT 'published'
        );

        CREATE INDEX IF NOT EXISTS idx_pricing_date
            ON pricing_records(check_date);
        CREATE INDEX IF NOT EXISTS idx_pricing_city
            ON pricing_records(city, state);
        CREATE INDEX IF NOT EXISTS idx_pricing_provider
            ON pricing_records(provider);
        CREATE INDEX IF NOT EXISTS idx_pricing_lookup
            ON pricing_records(check_date, city, provider, plan_name);

        CREATE TABLE IF NOT EXISTS check_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            status TEXT NOT NULL,
            cities_checked INTEGER DEFAULT 0,
            providers_checked INTEGER DEFAULT 0,
            plans_found INTEGER DEFAULT 0,
            errors TEXT
        );
    """
    )
    conn.commit()
    conn.close()


def store_plans(location: Location, plans: list[Plan], source: str = "published"):
    """Store pricing plans for a location."""
    conn = get_connection()
    now = datetime.now()
    timestamp = now.isoformat()
    check_date = now.strftime("%Y-%m-%d")

    for plan in plans:
        # Check if we already have this exact record today
        existing = conn.execute(
            """
            SELECT id, monthly_price FROM pricing_records
            WHERE check_date = ? AND city = ? AND provider = ? AND plan_name = ?
            """,
            (check_date, location.city, plan.provider, plan.plan_name),
        ).fetchone()

        if existing:
            # Update if price changed
            if existing["monthly_price"] != plan.monthly_price:
                conn.execute(
                    """
                    UPDATE pricing_records
                    SET monthly_price = ?, timestamp = ?, source = ?,
                        speed_down = ?, speed_up = ?, regular_price = ?
                    WHERE id = ?
                    """,
                    (
                        plan.monthly_price,
                        timestamp,
                        source,
                        plan.speed_down,
                        plan.speed_up,
                        plan.regular_price,
                        existing["id"],
                    ),
                )
        else:
            conn.execute(
                """
                INSERT INTO pricing_records
                (timestamp, check_date, city, state, address, zip_code,
                 provider, provider_type, plan_name, speed_down, speed_up,
                 monthly_price, is_introductory, intro_duration_months,
                 regular_price, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    timestamp,
                    check_date,
                    location.city,
                    location.state,
                    location.address,
                    location.zip_code,
                    plan.provider,
                    plan.provider_type,
                    plan.plan_name,
                    plan.speed_down,
                    plan.speed_up,
                    plan.monthly_price,
                    int(plan.is_introductory),
                    plan.intro_duration_months,
                    plan.regular_price,
                    source,
                ),
            )

    conn.commit()
    conn.close()


def log_check(status: str, cities: int, providers: int, plans: int, errors: str = ""):
    """Log a pricing check run."""
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO check_log (timestamp, status, cities_checked,
                               providers_checked, plans_found, errors)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (datetime.now().isoformat(), status, cities, providers, plans, errors),
    )
    conn.commit()
    conn.close()


def get_latest_pricing(city: Optional[str] = None) -> list[dict]:
    """Get the most recent pricing for all or a specific city."""
    conn = get_connection()

    # Find the latest check_date
    if city:
        row = conn.execute(
            "SELECT MAX(check_date) as d FROM pricing_records WHERE city = ?",
            (city,),
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT MAX(check_date) as d FROM pricing_records"
        ).fetchone()

    if not row or not row["d"]:
        conn.close()
        return []

    latest_date = row["d"]

    if city:
        rows = conn.execute(
            """
            SELECT * FROM pricing_records
            WHERE check_date = ? AND city = ?
            ORDER BY city, provider_type, provider, speed_down
            """,
            (latest_date, city),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT * FROM pricing_records
            WHERE check_date = ?
            ORDER BY city, provider_type, provider, speed_down
            """,
            (latest_date,),
        ).fetchall()

    conn.close()
    return [dict(r) for r in rows]


def get_pricing_history(
    days: int = 30,
    city: Optional[str] = None,
    provider: Optional[str] = None,
) -> list[dict]:
    """Get pricing history for charting."""
    conn = get_connection()

    query = """
        SELECT check_date, city, state, provider, provider_type,
               plan_name, speed_down, monthly_price, source
        FROM pricing_records
        WHERE check_date >= date('now', ?)
    """
    params: list = [f"-{days} days"]

    if city:
        query += " AND city = ?"
        params.append(city)
    if provider:
        query += " AND provider = ?"
        params.append(provider)

    query += " ORDER BY check_date, city, provider, speed_down"

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_check_dates() -> list[str]:
    """Get all dates where checks were performed."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT DISTINCT check_date FROM pricing_records ORDER BY check_date"
    ).fetchall()
    conn.close()
    return [r["check_date"] for r in rows]


def get_price_changes(days: int = 30) -> list[dict]:
    """Find price changes over the given period."""
    conn = get_connection()
    rows = conn.execute(
        """
        WITH ranked AS (
            SELECT *,
                LAG(monthly_price) OVER (
                    PARTITION BY city, provider, plan_name
                    ORDER BY check_date
                ) as prev_price,
                LAG(check_date) OVER (
                    PARTITION BY city, provider, plan_name
                    ORDER BY check_date
                ) as prev_date
            FROM pricing_records
            WHERE check_date >= date('now', ?)
        )
        SELECT * FROM ranked
        WHERE prev_price IS NOT NULL AND monthly_price != prev_price
        ORDER BY check_date DESC
        """,
        (f"-{days} days",),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
