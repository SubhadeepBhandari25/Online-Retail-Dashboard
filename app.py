"""
app.py - Flask website for the E-Commerce Customer and Product Data Management System.

Run:  python app.py      then open http://127.0.0.1:5000
"""

import os
from datetime import datetime

from flask import Flask, abort, render_template, request
from markupsafe import Markup, escape

from data_processing import DataStore, load_dataset
from generate_sample_data import make_sample

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

DATASET_NAME = "UCI Machine Learning Repository - Online Retail"
DATASET_URL = "https://archive.ics.uci.edu/dataset/352/online+retail"

app = Flask(__name__)


# ---------------------------------------------------------------------------
# Load the data once, when the server starts 
# ---------------------------------------------------------------------------
def find_dataset():
    """Use the real dataset if present, otherwise the generated sample."""
    candidates = [
        os.environ.get("DATA_FILE"),
        os.path.join(DATA_DIR, "online_retail.csv"),
        os.path.join(DATA_DIR, "online_retail.xlsx"),
    ]
    for path in candidates:
        if path and os.path.exists(path):
            return path, False
    sample = os.path.join(DATA_DIR, "sample_online_retail.csv")
    if not os.path.exists(sample):
        make_sample(sample)
    return sample, True


DATA_PATH, IS_SAMPLE = find_dataset()
_transactions, _report = load_dataset(DATA_PATH)
STORE = DataStore(_transactions, _report)
print(f"Loaded {len(_transactions):,} transactions from {os.path.basename(DATA_PATH)}")


# ---------------------------------------------------------------------------
# Template helpers
# ---------------------------------------------------------------------------
@app.template_filter("money")
def money(value):
    return f"£{value:,.2f}"


@app.template_filter("num")
def num(value):
    return f"{value:,}"


@app.template_global("tag")
def tag(text):
    """Small label naming the data structure behind a panel."""
    return Markup(f'<span class="tag" title="Data structure used">{escape(text)}</span>')


@app.context_processor
def inject_globals():
    return {
        "store": STORE,
        "is_sample": IS_SAMPLE,
        "dataset_name": DATASET_NAME,
        "dataset_url": DATASET_URL,
        "data_file": os.path.basename(DATA_PATH),
        "page": request.endpoint,
    }


def parse_date_arg(name):
    value = request.args.get(name, "")
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def int_arg(name, default=0):
    try:
        return max(int(request.args.get(name, default)), 0)
    except ValueError:
        return default


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route("/")
def dashboard():
    months = STORE.monthly_series()
    peak = max((v for _, v in months), default=1) or 1
    return render_template(
        "dashboard.html",
        summary=STORE.summary(),
        months=months,
        peak=peak,
        top_customers=STORE.top_customers(10),
        top_products=STORE.top_products(10, by="frequency"),
        countries=STORE.country_table()[:6],
        report=STORE.report,
    )


@app.route("/customers")
def customers():
    q = request.args.get("q", "")
    country = request.args.get("country", "")
    rows = STORE.customer_rows(q, country)
    return render_template(
        "customers.html", rows=rows[:100], total=len(rows),
        q=q, country=country, countries=sorted(STORE.countries),
    )


@app.route("/customers/<cid>")
def customer_detail(cid):
    if cid not in STORE.customers:
        abort(404)
    return render_template(
        "customer.html", cid=cid,
        row=STORE._customer_row(cid), history=STORE.customer_history(cid),
    )


@app.route("/products")
def products():
    q = request.args.get("q", "")
    sort = request.args.get("sort", "frequency")
    rows = STORE.product_rows(q, sort)
    return render_template("products.html", rows=rows[:100], total=len(rows), q=q, sort=sort)


@app.route("/products/<code>")
def product_detail(code):
    if code not in STORE.products:
        abort(404)
    return render_template("product.html", d=STORE.product_detail(code),
                           customer_country=STORE.customer_country)


@app.route("/transactions")
def transactions():
    country = request.args.get("country", "")
    invoice = request.args.get("invoice", "")
    text = request.args.get("text", "")
    min_qty = int_arg("min_qty")
    page_no = max(int_arg("page", 1), 1)
    per_page = 40

    matches = STORE.filter_transactions(
        country, invoice, text, min_qty,
        parse_date_arg("date_from"), parse_date_arg("date_to"),
    )
    start = (page_no - 1) * per_page
    # keep the filter in the pagination links
    keep = {k: v for k, v in request.args.items() if k != "page" and v}
    return render_template(
        "transactions.html", rows=matches[start:start + per_page], total=len(matches),
        page_no=page_no, pages=max((len(matches) + per_page - 1) // per_page, 1),
        countries=sorted(STORE.countries), keep=keep, args=request.args,
        revenue=round(sum(t.quantity * t.unit_price for t in matches), 2),
    )


@app.route("/countries")
def countries():
    a = request.args.get("a", "")
    b = request.args.get("b", "")
    comparison = None
    if a in STORE.countries and b in STORE.countries and a != b:
        comparison = STORE.compare_countries(a, b)
    return render_template(
        "countries.html", table=STORE.country_table(), names=sorted(STORE.countries),
        a=a, b=b, comparison=comparison,
    )


# ---------------------------------------------------------------------------
# Vercel fallback routes: in case requests reach Flask with /api/index prefix
# ---------------------------------------------------------------------------
@app.route("/api/index")
@app.route("/api/index/")
@app.route("/api")
@app.route("/api/")
def vercel_root():
    return dashboard()


@app.route("/api/index/static/<path:filename>")
@app.route("/api/static/<path:filename>")
def vercel_static(filename):
    return app.send_static_file(filename)


@app.route("/api/index/customers")
@app.route("/api/customers")
def vercel_customers():
    return customers()


@app.route("/api/index/customers/<cid>")
@app.route("/api/customers/<cid>")
def vercel_customer_detail(cid):
    return customer_detail(cid)


@app.route("/api/index/products")
@app.route("/api/products")
def vercel_products():
    return products()


@app.route("/api/index/products/<code>")
@app.route("/api/products/<code>")
def vercel_product_detail(code):
    return product_detail(code)


@app.route("/api/index/transactions")
@app.route("/api/transactions")
def vercel_transactions():
    return transactions()


@app.route("/api/index/countries")
@app.route("/api/countries")
def vercel_countries():
    return countries()


@app.errorhandler(404)
def not_found(_):
    return render_template("404.html"), 404


if __name__ == "__main__":
    app.run(debug=True)
