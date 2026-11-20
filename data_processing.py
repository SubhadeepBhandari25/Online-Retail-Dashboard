"""
data_processing.py
------------------
All the data-structure work for the project lives here, separate from the web
layer (app.py). Every major structure carries a comment explaining WHY it was
chosen, because that is the central objective of the assignment.

Dataset: UCI "Online Retail" (UK online gift retailer, 2010-2011)
URL    : https://archive.ics.uci.edu/dataset/352/online+retail
Also works with "Online Retail II" (column names differ slightly, handled below).
"""

import csv
from collections import namedtuple, defaultdict
from datetime import datetime

# --------------------------------------------------------------------------
# TUPLE (namedtuple) - one transaction line.
# WHY: a purchase that has already happened must never change, so an immutable
# record is the right fit. A namedtuple also lets us write t.quantity instead
# of t[3], and it uses less memory than a dict per row (important: ~400k rows).
# --------------------------------------------------------------------------
Transaction = namedtuple(
    "Transaction",
    "invoice stock_code description quantity unit_price date customer_id country",
)

# Different versions of the dataset name their columns differently.
# DICT used as a lookup table: our field name -> accepted header spellings.
COLUMN_ALIASES = {
    "invoice": ("invoiceno", "invoice"),
    "stock_code": ("stockcode",),
    "description": ("description",),
    "quantity": ("quantity",),
    "date": ("invoicedate",),
    "unit_price": ("unitprice", "price"),
    "customer_id": ("customerid",),
    "country": ("country",),
}

DATE_FORMATS = (
    "%m/%d/%Y %H:%M",
    "%Y-%m-%d %H:%M:%S",
    "%d/%m/%Y %H:%M",
    "%Y-%m-%d %H:%M",
    "%m/%d/%Y %H:%M:%S",
)

# SET: membership tests are O(1) and duplicates vanish automatically.
NON_PRODUCT_CODES = {"C2", "M", "D", "POST", "DOT", "CRUK", "BANK CHARGES", "AMAZONFEE"}


# ---------------------------------------------------------------------------
# STRING CLEANING
# ---------------------------------------------------------------------------
def clean_text(text):
    """strip() + split()/join() collapses stray spaces; upper() standardises case."""
    return " ".join(str(text or "").split()).upper()


def clean_country(text):
    """'  united   kingdom ' -> 'United Kingdom'"""
    return " ".join(str(text or "").split()).title()


def clean_customer_id(raw):
    """Spreadsheets often turn 17850 into '17850.0'. Strip that suffix."""
    return str(raw or "").strip().removesuffix(".0")


def parse_date(text):
    text = str(text).strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


# ---------------------------------------------------------------------------
# LOADING
# ---------------------------------------------------------------------------
def _read_rows(path):
    """Yield each row as a dict, from either .csv or .xlsx."""
    if path.lower().endswith((".xlsx", ".xlsm")):
        from openpyxl import load_workbook  # only needed for Excel files

        sheet = load_workbook(path, read_only=True).active
        rows = sheet.iter_rows(values_only=True)
        header = [str(h) for h in next(rows)]
        for values in rows:
            yield dict(zip(header, values))
    else:
        with open(path, newline="", encoding="utf-8-sig", errors="replace") as f:
            yield from csv.DictReader(f)


def _map_columns(header):
    """Match the file's header names to our field names using COLUMN_ALIASES."""
    normalised = {h.lower().replace(" ", ""): h for h in header}
    mapping = {}
    for field, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in normalised:
                mapping[field] = normalised[alias]
                break
    missing = set(COLUMN_ALIASES) - set(mapping)
    if missing:
        raise ValueError(f"Dataset is missing columns for: {sorted(missing)}")
    return mapping


def load_dataset(path):
    """
    Read the file and return (transactions, report).

    transactions -> LIST of Transaction tuples (ordered collection of records)
    report       -> DICT counting how many rows were dropped and why
    """
    transactions = []
    report = {"rows_read": 0, "no_customer": 0, "cancelled": 0,
              "bad_quantity_or_price": 0, "non_product": 0, "bad_date": 0}
    mapping = None
    m_cid = m_inv = m_sc = m_qty = m_up = m_dt = m_desc = m_cnt = None

    for row in _read_rows(path):
        if mapping is None:
            mapping = _map_columns(list(row.keys()))
            m_cid = mapping["customer_id"]
            m_inv = mapping["invoice"]
            m_sc = mapping["stock_code"]
            m_qty = mapping["quantity"]
            m_up = mapping["unit_price"]
            m_dt = mapping["date"]
            m_desc = mapping["description"]
            m_cnt = mapping["country"]

        report["rows_read"] += 1

        customer_id = clean_customer_id(row.get(m_cid))
        if not customer_id or customer_id.lower() == "none":
            report["no_customer"] += 1
            continue

        invoice = str(row.get(m_inv) or "").strip().upper()
        if invoice.startswith("C"):          # string method: cancellations start with C
            report["cancelled"] += 1
            continue

        stock_code = clean_text(row.get(m_sc))
        if stock_code in NON_PRODUCT_CODES or not any(ch.isdigit() for ch in stock_code):
            report["non_product"] += 1       # postage, bank charges, manual entries...
            continue

        try:
            quantity = int(float(row.get(m_qty)))
            unit_price = float(row.get(m_up))
        except (TypeError, ValueError):
            report["bad_quantity_or_price"] += 1
            continue
        if quantity <= 0 or unit_price <= 0:
            report["bad_quantity_or_price"] += 1
            continue

        date = row.get(m_dt)
        date = date if isinstance(date, datetime) else parse_date(date)
        if date is None:
            report["bad_date"] += 1
            continue

        transactions.append(
            Transaction(
                invoice, stock_code, clean_text(row.get(m_desc)) or "UNKNOWN",
                quantity, unit_price, date, customer_id, clean_country(row.get(m_cnt)),
            )
        )

    report["kept"] = len(transactions)
    return transactions, report


def line_total(t):
    return t.quantity * t.unit_price


# ---------------------------------------------------------------------------
# THE DATA STORE
# ---------------------------------------------------------------------------
class DataStore:
    """Builds every data structure once, then answers questions from them."""

    def __init__(self, transactions, report=None):
        self.report = report or {}
        self.transactions = transactions                       # LIST of tuples

        # --- SETS: "which unique things exist?" -------------------------
        self.customers = {t.customer_id for t in transactions}  # set comprehension
        self.products = {t.stock_code for t in transactions}
        self.countries = {t.country for t in transactions}
        self.invoice_ids = {t.invoice for t in transactions}

        # --- DICTIONARIES: "give me everything about X, instantly" ------
        # dict of lists:  customer id -> every transaction they made
        self.customer_purchases = defaultdict(list)
        # dict of dicts:  stock code -> running statistics for that product
        self.product_sales = {}
        # dict of lists:  invoice id -> its line items (an order/basket)
        self.invoices = defaultdict(list)
        # dict of sets:   country -> customers / products seen there
        self.country_customers = defaultdict(set)
        self.country_products = defaultdict(set)
        self.customer_country = {}
        # dict of floats: 'YYYY-MM' -> revenue
        self.monthly_revenue = defaultdict(float)

        for t in transactions:
            self.customer_purchases[t.customer_id].append(t)
            self.invoices[t.invoice].append(t)
            self.country_customers[t.country].add(t.customer_id)
            self.country_products[t.country].add(t.stock_code)
            self.customer_country[t.customer_id] = t.country
            self.monthly_revenue[t.date.strftime("%Y-%m")] += line_total(t)

            stats = self.product_sales.setdefault(
                t.stock_code,
                {"description": t.description, "quantity": 0, "revenue": 0.0,
                 "invoices": set(), "customers": set()},
            )
            stats["quantity"] += t.quantity
            stats["revenue"] += line_total(t)
            stats["invoices"].add(t.invoice)      # a SET so one order counts once
            stats["customers"].add(t.customer_id)

        # --- DICT COMPREHENSIONS: derived summaries -------------------
        self.customer_totals = {
            cid: round(sum(line_total(t) for t in rows), 2)
            for cid, rows in self.customer_purchases.items()
        }
        self.customer_orders = {
            cid: len({t.invoice for t in rows})
            for cid, rows in self.customer_purchases.items()
        }
        self.customer_quantity = {
            cid: sum(t.quantity for t in rows)
            for cid, rows in self.customer_purchases.items()
        }
        # purchase frequency = in how many different orders the product appeared
        self.product_frequency = {
            code: len(s["invoices"]) for code, s in self.product_sales.items()
        }

        self.total_quantity = sum(t.quantity for t in transactions)
        self.total_revenue = round(sum(self.customer_totals.values()), 2)

    # ------------------------------------------------------------------
    # SUMMARY FUNCTIONS
    # ------------------------------------------------------------------
    def summary(self):
        return {
            "unique_customers": len(self.customers),
            "unique_products": len(self.products),
            "unique_countries": len(self.countries),
            "total_transactions": len(self.transactions),
            "total_invoices": len(self.invoice_ids),
            "total_quantity": self.total_quantity,
            "total_revenue": self.total_revenue,
        }

    def top_customers(self, n=10):
        ranked = sorted(self.customer_totals.items(), key=lambda kv: kv[1], reverse=True)
        return [self._customer_row(cid) for cid, _ in ranked[:n]]

    def top_products(self, n=10, by="frequency"):
        return self.product_rows(sort=by)[:n]

    def monthly_series(self):
        """List of (month, revenue) tuples in chronological order."""
        return sorted(self.monthly_revenue.items())

    def country_table(self):
        rows = [
            {
                "country": c,
                "customers": len(self.country_customers[c]),
                "products": len(self.country_products[c]),
                "revenue": round(sum(self.customer_totals[cid]
                                     for cid in self.country_customers[c]), 2),
            }
            for c in self.countries
        ]
        return sorted(rows, key=lambda r: r["revenue"], reverse=True)

    # ------------------------------------------------------------------
    # CUSTOMERS
    # ------------------------------------------------------------------
    def _customer_row(self, cid):
        return {
            "id": cid,
            "country": self.customer_country[cid],
            "orders": self.customer_orders[cid],
            "quantity": self.customer_quantity[cid],
            "total": self.customer_totals[cid],
        }

    def customer_rows(self, query="", country=""):
        """SEARCH + FILTER with a list comprehension."""
        q = query.strip().lower()
        rows = [
            self._customer_row(cid)
            for cid in self.customers
            if (not q or q in cid.lower())
            and (not country or self.customer_country[cid] == country)
        ]
        return sorted(rows, key=lambda r: r["total"], reverse=True)

    def customer_history(self, cid):
        """
        NESTED structure: dict (invoice) -> dict (details) -> list (lines).
        Groups one customer's purchases into their original orders.
        """
        history = {}
        for t in self.customer_purchases[cid]:
            order = history.setdefault(
                t.invoice, {"date": t.date, "lines": [], "total": 0.0}
            )
            order["lines"].append(t)
            order["total"] += line_total(t)
        orders = sorted(history.items(), key=lambda kv: kv[1]["date"], reverse=True)

        favourite = {}
        for t in self.customer_purchases[cid]:
            favourite[t.stock_code] = favourite.get(t.stock_code, 0) + t.quantity
        top_items = sorted(favourite.items(), key=lambda kv: kv[1], reverse=True)[:5]
        return {
            "orders": orders,
            "top_items": [(code, self.product_sales[code]["description"], qty)
                          for code, qty in top_items],
        }

    # ------------------------------------------------------------------
    # PRODUCTS
    # ------------------------------------------------------------------
    def _product_row(self, code):
        s = self.product_sales[code]
        return {
            "code": code,
            "description": s["description"],
            "quantity": s["quantity"],
            "revenue": round(s["revenue"], 2),
            "frequency": self.product_frequency[code],
            "buyers": len(s["customers"]),
        }

    def product_rows(self, query="", sort="frequency"):
        q = query.strip().lower()
        rows = [
            self._product_row(code)
            for code, s in self.product_sales.items()
            if not q or q in code.lower() or q in s["description"].lower()
        ]
        if sort not in {"frequency", "quantity", "revenue", "buyers"}:
            sort = "frequency"
        return sorted(rows, key=lambda r: r[sort], reverse=True)

    def product_detail(self, code):
        s = self.product_sales[code]
        buyers = sorted(s["customers"])
        recent = sorted(
            (t for t in self.transactions if t.stock_code == code),
            key=lambda t: t.date, reverse=True,
        )[:25]
        countries = sorted({self.customer_country[c] for c in buyers})  # set comp
        return {"row": self._product_row(code), "buyers": buyers,
                "countries": countries, "recent": recent}

    # ------------------------------------------------------------------
    # TRANSACTION FILTER
    # ------------------------------------------------------------------
    def filter_transactions(self, country="", invoice="", text="",
                            min_quantity=0, date_from=None, date_to=None):
        text = text.strip().lower()
        invoice = invoice.strip().upper()
        return [
            t for t in self.transactions
            if (not country or t.country == country)
            and (not invoice or t.invoice == invoice)
            and (not text or text in t.description.lower() or text in t.stock_code.lower())
            and t.quantity >= min_quantity
            and (date_from is None or t.date.date() >= date_from)
            and (date_to is None or t.date.date() <= date_to)
        ]

    # ------------------------------------------------------------------
    # SET OPERATIONS
    # ------------------------------------------------------------------
    def compare_countries(self, a, b):
        pa, pb = self.country_products[a], self.country_products[b]
        ca, cb = self.country_customers[a], self.country_customers[b]
        return {
            "shared_products": sorted(pa & pb),          # intersection
            "only_a_products": sorted(pa - pb),          # difference
            "only_b_products": sorted(pb - pa),
            "all_products": len(pa | pb),                # union
            "shared_customers": sorted(ca & cb),         # customers active in both
        }

    def describe(self, code):
        return self.product_sales[code]["description"]
