"""Seeds the app DB with demo listings from the same CSV the ML model is trained on.

Runs on an app instance (the DB is private):  cd /opt/cloudscale/app && sudo -u cloudscale \
  env $(cat /etc/cloudscale.env | xargs) /opt/cloudscale/venv/bin/python seed_db.py
Idempotent: does nothing if seed rows already exist. Seed rows belong to users whose sub
starts with 'seed-' and can be removed with: DELETE FROM users WHERE sub LIKE 'seed-%' (after deleting their items).
"""
import csv
import os
import random

import db

CSV_PATH = os.path.join(os.path.dirname(__file__), "data", "seed_listings.csv")
COUNT = 36
SEED_USERS = [
    ("seed-1", "demo.ali@example.invalid", "Ali (demo)"),
    ("seed-2", "demo.sara@example.invalid", "Sara (demo)"),
    ("seed-3", "demo.hamza@example.invalid", "Hamza (demo)"),
]


def main():
    random.seed(11)
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    random.shuffle(rows)
    rows = rows[:COUNT]
    with db.get_conn() as conn:
        existing = conn.execute("SELECT count(*) AS n FROM items WHERE owner_sub LIKE 'seed-%%'").fetchone()["n"]
        if existing:
            print(f"seed data already present ({existing} items); nothing to do")
            return
        for sub, email, name in SEED_USERS:
            conn.execute(
                "INSERT INTO users (sub, email, display_name) VALUES (%s, %s, %s) ON CONFLICT (sub) DO NOTHING",
                (sub, email, name),
            )
        for i, r in enumerate(rows):
            title = r["title"]
            kind = "found" if title.lower().startswith("found") else "lost"
            conn.execute(
                """INSERT INTO items (owner_sub, kind, title, notes, description, category,
                                      ml_category, location, item_date)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, '', current_date - %s)""",
                (SEED_USERS[i % 3][0], kind, title, r["notes"], r["notes"].capitalize() + ".",
                 r["category"], r["category"], random.randint(0, 6)),
            )
        print(f"inserted {len(rows)} demo items for {len(SEED_USERS)} demo users")


if __name__ == "__main__":
    main()
