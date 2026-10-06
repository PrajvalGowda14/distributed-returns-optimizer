"""Generate deterministic, fictional synthetic data for three retailers.

Usage:
    python generate_data.py

Each retailer gets its own directory under ``data/`` with orders.csv,
returns.csv and support_cases.csv. No real companies or customers are used.

Planted scenarios (verified by the tests):
    1. Electronics COMPATIBILITY at all three retailers  -> High, Broad
    2. Footwear FIT_TOO_SMALL at retailers A and B       -> approved
    3. SETUP_DIFFICULTY at multiple retailers            -> approved
    4. Furniture DAMAGED at retailers A and B            -> approved
    5. Beauty allergy/sensitivity (OTHER) only at A      -> suppressed (diversity)
    6. Sports DAMAGED and Electronics DELIVERY_PROBLEM,
       fewer than five records in total                  -> suppressed
    7. DIMENSION_MISMATCH and EXPECTATION_MISMATCH       -> intervention examples
"""

from __future__ import annotations

import csv
import random
from datetime import date, timedelta
from pathlib import Path

SEED = 42
ORDERS_PER_RETAILER = 100
SUPPORT_CASES_PER_RETAILER = 40
DATA_DIR = Path(__file__).resolve().parent / "data"
START_DATE = date(2026, 7, 1)

PRODUCTS: dict[str, list[str]] = {
    "Electronics": ["Phone Case Nova", "USB-C Charger Volt", "Wireless Earbuds Echo", "Laptop Dock Hub",
                    "Smartwatch Band Loop", "Bluetooth Speaker Pulse"],
    "Footwear": ["Trail Runner Shoe", "Leather Ankle Boot", "Court Sneaker"],
    "Apparel": ["Linen Shirt", "Wool Sweater", "Denim Jacket", "Chino Trousers"],
    "Furniture": ["Oak Side Table", "Tall Bookshelf", "Two-Seat Sofa", "Compact Desk"],
    "Beauty": ["Face Serum", "Velvet Lipstick", "Body Lotion"],
    "Home": ["Area Rug", "Ceramic Vase", "Table Lamp", "Wall Mirror"],
    "Sports": ["Tennis Racket", "Yoga Mat"],
}

RETURN_REASON = {
    "COMPATIBILITY": "Incompatible with device",
    "FIT_TOO_SMALL": "Size issue",
    "FIT_TOO_LARGE": "Size issue",
    "EXPECTATION_MISMATCH": "Not as expected",
    "DIMENSION_MISMATCH": "Not as expected",
    "DAMAGED": "Arrived damaged",
    "SETUP_DIFFICULTY": "Difficult to use",
    "DELIVERY_PROBLEM": "Delivery issue",
    "OTHER": "Other",
}

# Comment templates keyed by (category, cause); falls back to (None, cause).
COMMENTS: dict[tuple[str | None, str], list[str]] = {
    ("Electronics", "COMPATIBILITY"): [
        "The case does not fit my phone.",
        "I selected the wrong device model.",
        "The accessory is incompatible.",
        "Charger is not compatible with my laptop.",
        "Dock does not work with my laptop, wrong model.",
        "Band is not supported on my watch, incompatible.",
    ],
    ("Electronics", "SETUP_DIFFICULTY"): [
        "Could not connect Bluetooth to the speaker.",
        "Pairing kept failing and the instructions were confusing.",
        "The setup app was confusing.",
        "Could not connect to wifi during setup.",
    ],
    (None, "SETUP_DIFFICULTY"): [
        "Assembly instructions were confusing.",
        "Could not assemble it, the instructions skip steps.",
        "Install guide was confusing.",
    ],
    ("Footwear", "FIT_TOO_SMALL"): [
        "Shoe was too tight.",
        "Runs small, toes felt cramped.",
        "Too small, I need to size up.",
        "Pinches at the heel, too tight.",
    ],
    ("Apparel", "FIT_TOO_SMALL"): [
        "Too tight across the shoulders.",
        "Runs small, I need to size up.",
        "Too small in the chest.",
    ],
    ("Footwear", "FIT_TOO_LARGE"): [
        "Boots were too big, my heel slips.",
        "Runs large, had to size down.",
        "Too loose even with thick socks.",
    ],
    ("Apparel", "FIT_TOO_LARGE"): [
        "Sleeves are too long.",
        "Shirt was much too large.",
        "Too loose around the waist.",
        "Runs large, had to size down.",
    ],
    (None, "EXPECTATION_MISMATCH"): [
        "Color looked different from the photo.",
        "The shade was not as pictured.",
        "Not what I expected, the material felt thin.",
        "Not as described, the colour is off.",
    ],
    ("Furniture", "DIMENSION_MISMATCH"): [
        "Table looked larger online.",
        "Shelf was smaller than expected.",
        "Sofa does not fit in my living room, please list dimensions clearly.",
        "Desk was bigger than expected for my room.",
    ],
    ("Home", "DIMENSION_MISMATCH"): [
        "Rug was smaller than it looked.",
        "Mirror looked larger online.",
        "Lamp was smaller than expected.",
    ],
    ("Furniture", "DAMAGED"): [
        "One leg was broken on arrival.",
        "Box was crushed and the top was scratched.",
        "Glass panel arrived broken.",
        "Corner arrived cracked.",
    ],
    ("Electronics", "DAMAGED"): ["Screen arrived cracked.", "Casing was dented and scratched."],
    ("Beauty", "DAMAGED"): ["Bottle arrived cracked and leaking.", "Compact arrived broken."],
    ("Sports", "DAMAGED"): ["Racket frame arrived cracked.", "Arrived damaged, the packaging was torn."],
    (None, "DAMAGED"): ["Arrived cracked.", "Vase arrived broken.", "Frame was chipped and scratched."],
    (None, "DELIVERY_PROBLEM"): [
        "Package was late.",
        "Delivery was delayed by a week.",
        "Arrived after the event, took too long.",
    ],
    ("Beauty", "OTHER"): [
        "Caused a rash on my skin.",
        "Skin irritation after one use.",
        "Allergic reaction to the fragrance.",
    ],
    (None, "OTHER"): [
        "Gift recipient did not want it.",
        "No longer needed.",
    ],
}

CONTACT_REASON = {
    "COMPATIBILITY": "Compatibility question",
    "FIT_TOO_SMALL": "Sizing question",
    "FIT_TOO_LARGE": "Sizing question",
    "EXPECTATION_MISMATCH": "Product question",
    "DIMENSION_MISMATCH": "Product question",
    "DAMAGED": "Damage report",
    "SETUP_DIFFICULTY": "Setup help",
    "DELIVERY_PROBLEM": "Delivery status",
    "OTHER": "General enquiry",
}

RESOLUTION = {
    "COMPATIBILITY": ["Exchange", "Refund", "Guidance"],
    "FIT_TOO_SMALL": ["Exchange", "Refund"],
    "FIT_TOO_LARGE": ["Exchange", "Refund"],
    "EXPECTATION_MISMATCH": ["Refund", "Store credit"],
    "DIMENSION_MISMATCH": ["Refund", "Exchange"],
    "DAMAGED": ["Replacement", "Refund"],
    "SETUP_DIFFICULTY": ["Guidance", "Escalated", "Refund"],
    "DELIVERY_PROBLEM": ["Refund", "Store credit"],
    "OTHER": ["Refund"],
}

# (category, cause, count) per retailer. Exact counts are local secrets of each retailer.
RETAILER_PLANS: dict[str, list[tuple[str, str, int]]] = {
    "A": [("Electronics", "COMPATIBILITY", 8), ("Electronics", "SETUP_DIFFICULTY", 4),
          ("Footwear", "FIT_TOO_SMALL", 6), ("Furniture", "DAMAGED", 4), ("Furniture", "DIMENSION_MISMATCH", 4),
          ("Beauty", "OTHER", 5), ("Apparel", "EXPECTATION_MISMATCH", 5), ("Apparel", "FIT_TOO_LARGE", 4),
          ("Home", "DELIVERY_PROBLEM", 4), ("Sports", "DAMAGED", 2), ("Electronics", "DELIVERY_PROBLEM", 1),
          ("Apparel", "FIT_TOO_SMALL", 4), ("Home", "DIMENSION_MISMATCH", 3), ("Footwear", "FIT_TOO_LARGE", 2),
          ("Electronics", "EXPECTATION_MISMATCH", 3), ("Home", "EXPECTATION_MISMATCH", 3),
          ("Furniture", "SETUP_DIFFICULTY", 3)],
    "B": [("Electronics", "COMPATIBILITY", 7), ("Electronics", "SETUP_DIFFICULTY", 4),
          ("Footwear", "FIT_TOO_SMALL", 5), ("Furniture", "DAMAGED", 5), ("Furniture", "DIMENSION_MISMATCH", 3),
          ("Apparel", "EXPECTATION_MISMATCH", 4), ("Apparel", "FIT_TOO_LARGE", 3), ("Home", "DELIVERY_PROBLEM", 3),
          ("Sports", "DAMAGED", 2), ("Electronics", "DELIVERY_PROBLEM", 1), ("Apparel", "FIT_TOO_SMALL", 3),
          ("Home", "DIMENSION_MISMATCH", 4), ("Home", "EXPECTATION_MISMATCH", 4),
          ("Furniture", "SETUP_DIFFICULTY", 3), ("Beauty", "EXPECTATION_MISMATCH", 4),
          ("Footwear", "EXPECTATION_MISMATCH", 3), ("Electronics", "DAMAGED", 2), ("Beauty", "DAMAGED", 2),
          ("Apparel", "OTHER", 2)],
    "C": [("Electronics", "COMPATIBILITY", 6), ("Electronics", "SETUP_DIFFICULTY", 5),
          ("Footwear", "FIT_TOO_SMALL", 1), ("Furniture", "DAMAGED", 2), ("Furniture", "DIMENSION_MISMATCH", 4),
          ("Apparel", "EXPECTATION_MISMATCH", 4), ("Apparel", "FIT_TOO_LARGE", 3), ("Home", "DELIVERY_PROBLEM", 4),
          ("Electronics", "DELIVERY_PROBLEM", 2), ("Apparel", "FIT_TOO_SMALL", 4), ("Home", "DIMENSION_MISMATCH", 3),
          ("Home", "EXPECTATION_MISMATCH", 3), ("Beauty", "EXPECTATION_MISMATCH", 4),
          ("Home", "SETUP_DIFFICULTY", 4), ("Electronics", "EXPECTATION_MISMATCH", 4),
          ("Footwear", "FIT_TOO_LARGE", 3), ("Apparel", "DELIVERY_PROBLEM", 3), ("Beauty", "DELIVERY_PROBLEM", 3),
          ("Home", "DAMAGED", 3)],
}

EXCHANGE_CATEGORIES = {"Electronics", "Footwear", "Apparel"}


def _comment(rng: random.Random, category: str, cause: str) -> str:
    options = COMMENTS.get((category, cause)) or COMMENTS[(None, cause)]
    return rng.choice(options)


def _date(rng: random.Random) -> str:
    return (START_DATE + timedelta(days=rng.randint(0, 60))).isoformat()


def _write(path: Path, rows: list[dict]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def generate_retailer(letter: str, rng: random.Random) -> dict[str, list[dict]]:
    """Build orders, returns and support cases for one retailer."""
    retailer_id = f"RETAILER_{letter}"
    plan = [(cat, cause) for cat, cause, n in RETAILER_PLANS[letter] for _ in range(n)]
    rng.shuffle(plan)

    orders, returns = [], []
    for i, (category, cause) in enumerate(plan, start=1):
        order_id = f"{letter}-ORD-{i:04d}"
        product = rng.choice(PRODUCTS[category])
        delivery = "Delivered late" if cause == "DELIVERY_PROBLEM" else "Delivered"
        event_date = _date(rng)
        orders.append(dict(order_id=order_id, retailer_id=retailer_id, product_category=category,
                           product_name=product, delivery_status=delivery,
                           exchange_available=category in EXCHANGE_CATEGORIES or rng.random() < 0.3,
                           event_date=event_date))
        returns.append(dict(return_id=f"{letter}-RET-{i:04d}", order_id=order_id, retailer_id=retailer_id,
                            product_category=category, product_name=product, return_reason=RETURN_REASON[cause],
                            customer_comment=_comment(rng, category, cause), delivery_status=delivery,
                            support_contacted=False,
                            return_outcome=rng.choice(["Refund", "Exchange", "Store credit"]),
                            event_date=event_date, _cause=cause))

    categories = list(PRODUCTS)
    for i in range(len(plan) + 1, ORDERS_PER_RETAILER + 1):
        category = rng.choice(categories)
        orders.append(dict(order_id=f"{letter}-ORD-{i:04d}", retailer_id=retailer_id, product_category=category,
                           product_name=rng.choice(PRODUCTS[category]),
                           delivery_status=rng.choice(["Delivered", "Delivered", "Delivered", "Delivered late",
                                                       "In transit"]),
                           exchange_available=category in EXCHANGE_CATEGORIES or rng.random() < 0.3,
                           event_date=_date(rng)))

    n_from_returns = SUPPORT_CASES_PER_RETAILER - 6
    contacted = rng.sample(range(len(returns)), n_from_returns)
    cases = []
    for j, idx in enumerate(sorted(contacted), start=1):
        r = returns[idx]
        r["support_contacted"] = True
        cases.append(dict(case_id=f"{letter}-CASE-{j:04d}", order_id=r["order_id"], retailer_id=retailer_id,
                          contact_reason=CONTACT_REASON[r["_cause"]],
                          case_status=rng.choice(["Closed", "Closed", "Open"]),
                          resolution_type=rng.choice(RESOLUTION[r["_cause"]]),
                          sentiment=rng.choice(["Negative", "Negative", "Neutral", "Positive"]),
                          event_date=r["event_date"]))
    for j, order in enumerate(rng.sample(orders[len(plan):], 6), start=n_from_returns + 1):
        cases.append(dict(case_id=f"{letter}-CASE-{j:04d}", order_id=order["order_id"], retailer_id=retailer_id,
                          contact_reason=rng.choice(["Delivery status", "Product question"]),
                          case_status="Closed", resolution_type="Guidance",
                          sentiment=rng.choice(["Neutral", "Positive"]), event_date=order["event_date"]))

    for r in returns:
        del r["_cause"]
    return dict(orders=orders, returns=returns, support_cases=cases)


def main() -> None:
    """Regenerate all retailer datasets with a fixed seed."""
    rng = random.Random(SEED)
    for letter in RETAILER_PLANS:
        data = generate_retailer(letter, rng)
        out = DATA_DIR / f"retailer_{letter.lower()}"
        out.mkdir(parents=True, exist_ok=True)
        for name, rows in data.items():
            _write(out / f"{name}.csv", rows)
        print(f"retailer_{letter.lower()}: {len(data['orders'])} orders, {len(data['returns'])} returns, "
              f"{len(data['support_cases'])} support cases")


if __name__ == "__main__":
    main()
