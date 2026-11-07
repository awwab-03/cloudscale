"""Generates ml/data/seed_listings.csv: synthetic, campus-flavoured lost/found listings.

Deterministic (fixed seed). 8 categories x 50 rows = 400 rows. Synthetic by design: it is
template-generated, not scraped or collected from real users (stated honestly in the report).
"""
import csv
import os
import random

random.seed(2026)

LOCATIONS = [
    "library", "cafeteria", "CS block", "EE block", "main auditorium", "sports complex",
    "parking lot", "bus stop", "Lab 3", "admin block", "mosque", "ground floor corridor",
    "girls hostel gate", "boys hostel", "seminar hall", "tuck shop", "basketball court",
    "reading room", "photocopy shop", "Block C stairs",
]
TIMES = ["this morning", "yesterday", "after the 10am class", "after the lab", "last evening",
         "around lunch time", "during the quiz", "on Monday", "on Thursday", "after the society event"]
COLORS = ["black", "blue", "red", "grey", "white", "green", "navy", "brown", "pink", "silver", "maroon"]

CATEGORIES = {
    "Electronics": {
        "items": ["{c} Samsung phone", "iPhone with cracked screen", "Infinix phone with {c} cover",
                  "Oppo phone", "Xiaomi Redmi phone", "AirPods case", "{c} wireless earbuds",
                  "laptop charger", "Dell laptop charger", "{c} power bank", "{c} USB flash drive",
                  "Casio fx-991 scientific calculator", "smart watch", "wireless mouse",
                  "over-ear headphones", "tablet with {c} case", "HP laptop", "phone charger cable",
                  "Bluetooth speaker", "Arduino board"],
        "notes": ["battery was almost dead", "has a sticker on the back", "screen lock is on",
                  "left it charging near the socket", "contains my project files",
                  "has a small scratch on the side", "name is written inside the cover"],
    },
    "ID/Cards": {
        "items": ["student ID card", "FAST student card", "CNIC", "ATM card", "debit card",
                  "driving license", "library card", "bus pass card", "student card with {c} lanyard",
                  "national ID card", "Meezan bank card", "HBL debit card", "exam entry card",
                  "hostel access card", "society membership card"],
        "notes": ["name and roll number are printed on it", "photo ID, please return to admin",
                  "found on the floor", "has my roll number 22i", "chip card with a scratch",
                  "needed urgently for the exam", "please contact the owner"],
    },
    "Bags": {
        "items": ["{c} backpack", "{c} laptop bag", "{c} tote bag", "{c} leather wallet", "ladies purse",
                  "{c} pencil pouch", "gym bag", "{c} handbag", "sling bag", "drawstring bag",
                  "{c} messenger bag", "small coin purse", "Adidas backpack", "Nike gym bag",
                  "bag with notebooks inside"],
        "notes": ["zipper is slightly broken", "has a keychain on the zip", "contains some cash",
                  "my lab coat is inside", "has a tag with my name", "water stain on the bottom",
                  "front pocket has a charger"],
    },
    "Keys": {
        "items": ["house keys", "car key", "Honda car key with remote", "bike key", "hostel room key",
                  "keys with a {c} keychain", "locker key", "motorcycle key", "set of three keys",
                  "key with a football keychain", "Suzuki key fob", "bunch of keys on a ring",
                  "office room key", "padlock key", "Toyota key"],
        "notes": ["on a metal ring", "has a small bottle opener attached", "tagged with room 214",
                  "one key is slightly bent", "rubber cover on the head", "found near the gate",
                  "need it to get into my room"],
    },
    "Clothing": {
        "items": ["{c} hoodie", "{c} jacket", "{c} shawl", "{c} dupatta", "{c} cap", "wool gloves",
                  "white sneakers", "{c} sweater", "scarf", "blazer", "sports shoes", "{c} sweatshirt",
                  "lab coat", "{c} T-shirt", "football jersey"],
        "notes": ["size medium", "left on the chair", "has a university logo", "a bit muddy",
                  "brand tag still inside", "left after the sports event", "very warm one"],
    },
    "Books/Stationery": {
        "items": ["Calculus textbook", "Data Structures book", "Operating Systems textbook",
                  "{c} notebook", "lab manual", "pen set", "geometry box", "{c} folder with notes",
                  "highlighters", "Discrete Math book", "spiral notebook", "drawing sheets and pencils",
                  "Physics textbook", "assignment file", "stapler and pens", "Algorithms by Cormen"],
        "notes": ["my name is on the first page", "lots of highlighted notes", "has sticky tabs",
                  "assignment is due tomorrow", "left on the desk", "cover is torn",
                  "needed for the midterm"],
    },
    "Bottles/Accessories": {
        "items": ["{c} water bottle", "steel thermos", "Milton water bottle", "sunglasses", "spectacles",
                  "prescription glasses with {c} frame", "wrist watch", "umbrella", "lunch box",
                  "silver bracelet", "gold ring", "{c} insulated flask", "Casio watch", "earrings",
                  "hair clip", "{c} umbrella", "necklace"],
        "notes": ["has a dent on the side", "sticker of a cartoon on it", "leaking a bit",
                  "needed for daily use", "left on the bench", "very sentimental", "case is missing"],
    },
    "Other": {
        "items": ["football", "tennis racket", "cricket bat", "badminton racket", "bicycle helmet",
                  "{c} lanyard", "guitar", "art supplies box", "skateboard", "frisbee", "tripod stand",
                  "lab goggles", "chess set", "board game box", "microscope slide box", "extension board"],
        "notes": ["belongs to the sports society", "left after practice", "no name on it",
                  "found near the ground", "heavy, please collect from admin", "needed for the event",
                  "tied with a rope"],
    },
}

PER_CATEGORY = 50


def build():
    rows = []
    for cat, spec in CATEGORIES.items():
        seen = set()
        attempts = 0
        while len(seen) < PER_CATEGORY and attempts < 5000:
            attempts += 1
            title = random.choice(spec["items"]).format(c=random.choice(COLORS))
            verb = random.choice(["Lost", "Found", "Missing", "Found near", "Lost near"])
            loc = random.choice(LOCATIONS)
            if verb.endswith("near"):
                headline = f"{verb} {loc}: {title}"
            else:
                headline = f"{verb}: {title}"
            note = (f"{title} {random.choice(['seen', 'left', 'dropped', 'forgotten'])} at the {loc} "
                    f"{random.choice(TIMES)}, {random.choice(spec['notes'])}")
            if headline in seen:
                continue
            seen.add(headline)
            rows.append((headline, note, cat))
    random.shuffle(rows)
    return rows


if __name__ == "__main__":
    rows = build()
    out = os.path.join(os.path.dirname(__file__), "data", "seed_listings.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["title", "notes", "category"])
        w.writerows(rows)
    print(f"wrote {len(rows)} rows to {out}")
