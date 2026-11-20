"""
generate_sample_data.py
-----------------------
Creates data/sample_online_retail.csv in the SAME format as the UCI Online Retail
dataset (including some deliberately messy rows), so the website runs
immediately. Replace it with the real dataset for your submission:

    https://archive.ics.uci.edu/dataset/352/online+retail
    -> save as data/online_retail.csv  (or .xlsx)
"""

import csv
import os
import random
from datetime import datetime, timedelta

PRODUCTS = [
    ("85123A", "WHITE HANGING HEART T-LIGHT HOLDER", 2.55),
    ("71053", "WHITE METAL LANTERN", 3.39),
    ("84406B", "CREAM CUPID HEARTS COAT HANGER", 2.75),
    ("22423", "REGENCY CAKESTAND 3 TIER", 12.75),
    ("47566", "PARTY BUNTING", 4.95),
    ("84029G", "KNITTED UNION FLAG HOT WATER BOTTLE", 3.39),
    ("22086", "PAPER CHAIN KIT 50'S CHRISTMAS", 2.55),
    ("21730", "GLASS STAR FROSTED T-LIGHT HOLDER", 4.25),
    ("22633", "HAND WARMER UNION JACK", 1.85),
    ("22632", "HAND WARMER RED POLKA DOT", 1.85),
    ("84879", "ASSORTED COLOUR BIRD ORNAMENT", 1.69),
    ("22745", "POPPY'S PLAYHOUSE BEDROOM", 2.10),
    ("22748", "POPPY'S PLAYHOUSE KITCHEN", 2.10),
    ("22960", "JAM MAKING SET WITH JARS", 4.25),
    ("21212", "PACK OF 72 RETROSPOT CAKE CASES", 0.55),
    ("23084", "RABBIT NIGHT LIGHT", 2.08),
    ("22197", "SMALL POPCORN HOLDER", 0.85),
    ("85099B", "JUMBO BAG RED RETROSPOT", 2.08),
    ("22386", "JUMBO BAG PINK POLKADOT", 2.08),
    ("21931", "JUMBO STORAGE BAG SUKI", 2.08),
    ("20725", "LUNCH BAG RED RETROSPOT", 1.65),
    ("22727", "ALARM CLOCK BAKELIKE RED", 3.75),
    ("22728", "ALARM CLOCK BAKELIKE PINK", 3.75),
    ("22423B", "SET OF 3 CAKE TINS PANTRY DESIGN", 4.95),
    ("23166", "MEDIUM CERAMIC TOP STORAGE JAR", 1.04),
    ("22910", "PAPER CHAIN KIT VINTAGE CHRISTMAS", 2.95),
    ("21175", "GIN + TONIC DIET METAL SIGN", 2.10),
    ("22178", "VICTORIAN GLASS HANGING T-LIGHT", 1.25),
    ("22469", "HEART OF WICKER SMALL", 1.65),
    ("22470", "HEART OF WICKER LARGE", 2.95),
    ("23203", "JUMBO BAG DOILEY PATTERNS", 2.08),
    ("22111", "SCOTTIE DOG HOT WATER BOTTLE", 4.95),
    ("21977", "PACK OF 60 PINK PAISLEY CAKE CASES", 0.55),
    ("22139", "RETROSPOT TEA SET CERAMIC 11 PC", 4.95),
    ("23298", "SPOTTY BUNTING", 4.95),
    ("21034", "REX CASH+CARRY JUMBO SHOPPER", 0.95),
    ("22355", "CHARLOTTE BAG SUKI DESIGN", 0.85),
    ("22356", "CHARLOTTE BAG PINK POLKADOT", 0.85),
    ("20727", "LUNCH BAG BLACK SKULL", 1.65),
    ("22382", "LUNCH BAG SPACEBOY DESIGN", 1.65),
]
COUNTRIES = ["United Kingdom"] * 12 + ["Germany"] * 2 + ["France"] * 2 + \
            ["EIRE", "Spain", "Netherlands", "Belgium", "Australia"]


def make_sample(path, customers=250, invoices=1800, seed=7):
    rng = random.Random(seed)
    customer_ids = [str(rng.randint(12350, 18280)) for _ in range(customers)]
    home = {c: rng.choice(COUNTRIES) for c in customer_ids}
    start = datetime(2010, 12, 1, 8, 0)
    os.makedirs(os.path.dirname(path), exist_ok=True)

    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["InvoiceNo", "StockCode", "Description", "Quantity",
                    "InvoiceDate", "UnitPrice", "CustomerID", "Country"])
        for n in range(invoices):
            invoice = str(536365 + n)
            cust = rng.choice(customer_ids)
            when = start + timedelta(days=rng.randint(0, 364), hours=rng.randint(0, 9),
                                     minutes=rng.randint(0, 59))
            stamp = f"{when.month}/{when.day}/{when.year} {when.hour}:{when.minute:02d}"
            for code, desc, price in rng.sample(PRODUCTS, rng.randint(1, 8)):
                qty = rng.choice([1, 2, 3, 4, 6, 6, 8, 12, 12, 24])
                dirty = rng.random()
                # messy rows the cleaning code must handle
                if dirty < 0.03:
                    desc = "  " + desc.lower() + "  "
                country = home[cust] if dirty > 0.02 else home[cust].lower()
                cid = cust if dirty > 0.04 else ""
                w.writerow([invoice, code, desc, qty, stamp, price, cid, country])
            if rng.random() < 0.04:  # a cancellation
                code, desc, price = rng.choice(PRODUCTS)
                w.writerow(["C" + invoice, code, desc, -2, stamp, price, cust, home[cust]])
            if rng.random() < 0.05:  # postage line
                w.writerow([invoice, "POST", "POSTAGE", 1, stamp, 18.0, cust, home[cust]])
    return path


if __name__ == "__main__":
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data",
                       "sample_online_retail.csv")
    print("Wrote", make_sample(out))
