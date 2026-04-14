#!/usr/bin/env python3
"""Generate a static HTML export of the dashboard."""

import json
import os
import sys

# Use Flask's test client to render the template with real data
from dashboard import app, get_dashboard_data
from broadband_pricing.database import init_db
from broadband_pricing.config import OUTPUT_DIR

init_db()

with app.test_request_context():
    data = get_dashboard_data()
    if not data:
        print("No pricing data found. Run: python app.py check")
        sys.exit(1)

    rendered = app.jinja_env.get_template("dashboard.html").render(
        data=data,
        data_json=json.dumps(data, default=str),
    )

os.makedirs(OUTPUT_DIR, exist_ok=True)
out_path = os.path.join(OUTPUT_DIR, "dashboard.html")
with open(out_path, "w") as f:
    f.write(rendered)

print(f"Static dashboard saved to: {out_path}")
