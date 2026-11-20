"""
streamlit_app.py - Interactive Streamlit Dashboard for Online Retail Data
"""

import os
import datetime
import pandas as pd
import streamlit as st

from data_processing import DataStore, load_dataset
from generate_sample_data import make_sample

# Page configuration
st.set_page_config(
    page_title="Retail Data Desk",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")


@st.cache_resource(show_spinner="Loading and indexing retail transactions...")
def get_store():
    candidates = [
        os.environ.get("DATA_FILE"),
        os.path.join(DATA_DIR, "online_retail.csv"),
        os.path.join(DATA_DIR, "online_retail.xlsx"),
    ]
    for path in candidates:
        if path and os.path.exists(path):
            t, r = load_dataset(path)
            return DataStore(t, r), os.path.basename(path), False
    sample = os.path.join(DATA_DIR, "sample_online_retail.csv")
    if not os.path.exists(sample):
        make_sample(sample)
    t, r = load_dataset(sample)
    return DataStore(t, r), os.path.basename(sample), True


store, data_file, is_sample = get_store()

# Sidebar
st.sidebar.title("🛍️ Retail Data Desk")
if is_sample:
    st.sidebar.warning("Viewing sample dataset. Add online_retail.csv for full data.")
else:
    st.sidebar.success(f"Dataset: `{data_file}` ({len(store.transactions):,} rows)")

nav = st.sidebar.radio(
    "Go to",
    ["📊 Dashboard", "👥 Customers", "📦 Products", "🧾 Transactions", "🌍 Countries"],
)

st.sidebar.markdown("---")
st.sidebar.caption("Data Source: [UCI Machine Learning Repository](https://archive.ics.uci.edu/dataset/352/online+retail)")


# ---------------------------------------------------------------------------
# 1. DASHBOARD
# ---------------------------------------------------------------------------
if nav == "📊 Dashboard":
    st.title("Customer and Product Overview")
    st.caption("Real-time metrics computed in-memory using Python data structures.")

    summary = store.summary()
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Unique Customers", f"{summary['unique_customers']:,}")
    c2.metric("Unique Products", f"{summary['unique_products']:,}")
    c3.metric("Transactions", f"{summary['total_transactions']:,}")
    c4.metric("Orders (Invoices)", f"{summary['total_invoices']:,}")
    c5.metric("Units Purchased", f"{summary['total_quantity']:,}")
    c6.metric("Total Revenue", f"£{summary['total_revenue']:,.2f}")

    st.markdown("---")
    st.subheader("Revenue by Month")
    months = store.monthly_series()
    df_months = pd.DataFrame(months, columns=["Month", "Revenue (£)"])
    st.bar_chart(df_months.set_index("Month"), color="#0e6e6a")

    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Top Customers by Spend")
        top_c = store.top_customers(10)
        df_c = pd.DataFrame([
            {
                "Customer ID": c.id,
                "Country": c.country,
                "Orders": c.orders,
                "Total (£)": f"£{c.total:,.2f}",
            }
            for c in top_c
        ])
        st.dataframe(df_c, hide_index=True, use_container_width=True)

    with col_right:
        st.subheader("Most Frequently Purchased Products")
        top_p = store.top_products(10, by="frequency")
        df_p = pd.DataFrame([
            {
                "Stock Code": p.code,
                "Product": p.description.title(),
                "In Orders": p.frequency,
                "Units Sold": f"{p.quantity:,}",
            }
            for p in top_p
        ])
        st.dataframe(df_p, hide_index=True, use_container_width=True)

    c_c1, c_c2 = st.columns(2)
    with c_c1:
        st.subheader("Leading Countries")
        countries = store.country_table()[:8]
        df_cnt = pd.DataFrame([
            {
                "Country": name,
                "Customers": f"{count:,}",
                "Revenue (£)": f"£{rev:,.2f}",
            }
            for name, count, rev in countries
        ])
        st.dataframe(df_cnt, hide_index=True, use_container_width=True)

    with c_c2:
        st.subheader("What the Cleaning Step Removed")
        rep = store.report
        df_rep = pd.DataFrame([
            {"Step": "Rows read from file", "Count": f"{rep.get('rows_read', 0):,}"},
            {"Step": "No customer ID", "Count": f"{rep.get('no_customer', 0):,}"},
            {"Step": "Cancelled invoices (start with C)", "Count": f"{rep.get('cancelled', 0):,}"},
            {"Step": "Postage, fees & manual entries", "Count": f"{rep.get('non_product', 0):,}"},
            {"Step": "Zero or negative quantity/price", "Count": f"{rep.get('bad_quantity_or_price', 0):,}"},
            {"Step": "Cleaned transactions kept", "Count": f"{rep.get('kept', 0):,}"},
        ])
        st.dataframe(df_rep, hide_index=True, use_container_width=True)


# ---------------------------------------------------------------------------
# 2. CUSTOMERS
# ---------------------------------------------------------------------------
elif nav == "👥 Customers":
    st.title("Customer Directory & Purchase History")

    c1, c2 = st.columns([2, 1])
    q = c1.text_input("Search Customer ID", placeholder="e.g. 14646, 17850...")
    all_countries = ["All Countries"] + sorted(store.countries)
    selected_country = c2.selectbox("Filter by Country", all_countries)
    country_filter = "" if selected_country == "All Countries" else selected_country

    rows = store.customer_rows(q, country_filter)
    st.write(f"Showing **{min(len(rows), 100)}** of **{len(rows):,}** matching customers")

    df_cust = pd.DataFrame([
        {
            "Customer ID": r["id"],
            "Country": r["country"],
            "Orders": r["orders"],
            "Items Bought": r["items"],
            "Total Spend (£)": f"£{r['total']:,.2f}",
        }
        for r in rows[:100]
    ])
    st.dataframe(df_cust, hide_index=True, use_container_width=True)

    st.markdown("---")
    st.subheader("Customer Drill-down")
    cust_id_input = st.text_input("Enter Customer ID to view order history", value=rows[0]["id"] if rows else "")

    if cust_id_input and cust_id_input in store.customers:
        history = store.customer_history(cust_id_input)
        info = store._customer_row(cust_id_input)
        st.markdown(f"**Customer {cust_id_input}** — {info['country']} | **{info['orders']}** orders | **£{info['total']:,.2f}** total spend")

        for inv in history:
            with st.expander(f"Invoice {inv['invoice']} — {inv['date'].strftime('%Y-%m-%d %H:%M')} — Total: £{inv['total']:,.2f} ({len(inv['lines'])} items)"):
                df_lines = pd.DataFrame([
                    {
                        "Stock Code": t.stock_code,
                        "Description": t.description.title(),
                        "Quantity": t.quantity,
                        "Unit Price": f"£{t.unit_price:,.2f}",
                        "Line Total": f"£{t.quantity * t.unit_price:,.2f}",
                    }
                    for t in inv["lines"]
                ])
                st.dataframe(df_lines, hide_index=True, use_container_width=True)
    elif cust_id_input:
        st.warning(f"Customer ID '{cust_id_input}' not found.")


# ---------------------------------------------------------------------------
# 3. PRODUCTS
# ---------------------------------------------------------------------------
elif nav == "📦 Products":
    st.title("Product Catalog & Search")

    c1, c2 = st.columns([2, 1])
    q_prod = c1.text_input("Search Product Name or Stock Code", placeholder="e.g. Heart, Bag, 85123A...")
    sort_choice = c2.selectbox("Sort By", ["frequency", "quantity", "revenue"], format_func=lambda x: {
        "frequency": "Most Orders (Frequency)",
        "quantity": "Most Units Sold",
        "revenue": "Highest Revenue",
    }[x])

    p_rows = store.product_rows(q_prod, sort_choice)
    st.write(f"Showing **{min(len(p_rows), 100)}** of **{len(p_rows):,}** matching products")

    df_products = pd.DataFrame([
        {
            "Stock Code": r["code"],
            "Description": r["description"].title(),
            "Orders": r["frequency"],
            "Units Sold": f"{r['quantity']:,}",
            "Revenue (£)": f"£{r['revenue']:,.2f}",
        }
        for r in p_rows[:100]
    ])
    st.dataframe(df_products, hide_index=True, use_container_width=True)

    st.markdown("---")
    st.subheader("Product Drill-down")
    code_input = st.text_input("Enter Stock Code to inspect", value=p_rows[0]["code"] if p_rows else "")
    if code_input and code_input in store.products:
        detail = store.product_detail(code_input)
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Stock Code", detail["code"])
        col2.metric("In Orders", f"{detail['frequency']:,}")
        col3.metric("Units Sold", f"{detail['quantity']:,}")
        col4.metric("Revenue", f"£{detail['revenue']:,.2f}")

        st.write(f"**Description:** {detail['description'].title()}")
        st.write(f"Purchased across **{len(detail['countries'])}** countries:")
        st.write(", ".join(sorted(detail["countries"])))


# ---------------------------------------------------------------------------
# 4. TRANSACTIONS
# ---------------------------------------------------------------------------
elif nav == "🧾 Transactions":
    st.title("Transaction Explorer")

    with st.expander("Filter Options", expanded=True):
        c1, c2, c3 = st.columns(3)
        cnt = c1.selectbox("Country", ["All Countries"] + sorted(store.countries))
        cnt_val = "" if cnt == "All Countries" else cnt
        txt = c2.text_input("Description keyword", placeholder="e.g. box, lantern...")
        min_q = c3.number_input("Minimum Quantity", min_value=0, value=0, step=1)

        c4, c5 = st.columns(2)
        inv_search = c4.text_input("Invoice Number", placeholder="e.g. 536365...")
        date_range = c5.date_input(
            "Invoice Date Range",
            value=[],
        )

    date_from = date_range[0] if len(date_range) > 0 else None
    date_to = date_range[1] if len(date_range) > 1 else None

    matches = store.filter_transactions(
        country=cnt_val,
        invoice=inv_search,
        text=txt,
        min_qty=min_q,
        date_from=date_from,
        date_to=date_to,
    )

    tot_rev = sum(t.quantity * t.unit_price for t in matches)
    st.info(f"Found **{len(matches):,}** matching transactions (Combined Total: **£{tot_rev:,.2f}**)")

    # Display first 200 matches
    df_tx = pd.DataFrame([
        {
            "Invoice": t.invoice,
            "Date": t.date.strftime("%Y-%m-%d %H:%M"),
            "Stock Code": t.stock_code,
            "Description": t.description.title(),
            "Qty": t.quantity,
            "Price (£)": f"£{t.unit_price:,.2f}",
            "Total (£)": f"£{t.quantity * t.unit_price:,.2f}",
            "Customer ID": t.customer_id,
            "Country": t.country,
        }
        for t in matches[:200]
    ])
    st.dataframe(df_tx, hide_index=True, use_container_width=True)
    if len(matches) > 200:
        st.caption(f"Showing first 200 of {len(matches):,} rows.")


# ---------------------------------------------------------------------------
# 5. COUNTRIES
# ---------------------------------------------------------------------------
elif nav == "🌍 Countries":
    st.title("Geographical Analysis & Comparisons")

    st.subheader("Country Revenue & Customer Table")
    cnt_table = store.country_table()
    df_all_cnt = pd.DataFrame([
        {
            "Country": c[0],
            "Unique Customers": f"{c[1]:,}",
            "Total Revenue (£)": f"£{c[2]:,.2f}",
        }
        for c in cnt_table
    ])
    st.dataframe(df_all_cnt, hide_index=True, use_container_width=True)

    st.markdown("---")
    st.subheader("Compare Two Countries (Set Operations)")
    c1, c2 = st.columns(2)
    names = sorted(store.countries)
    country_a = c1.selectbox("Country A", names, index=names.index("France") if "France" in names else 0)
    country_b = c2.selectbox("Country B", names, index=names.index("Germany") if "Germany" in names else 1)

    if country_a != country_b:
        cmp = store.compare_countries(country_a, country_b)

        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("Products in Both (Intersection)", f"{cmp['both_count']:,}")
        col_m2.metric(f"Exclusive to {country_a}", f"{cmp['only_a_count']:,}")
        col_m3.metric(f"Exclusive to {country_b}", f"{cmp['only_b_count']:,}")

        t1, t2, t3 = st.tabs(["Common Products", f"Exclusive to {country_a}", f"Exclusive to {country_b}"])
        with t1:
            st.write(f"**{cmp['both_count']}** products bought in both {country_a} and {country_b}:")
            st.write(", ".join(sorted(cmp["both_products"])))
        with t2:
            st.write(f"**{cmp['only_a_count']}** products bought only in {country_a}:")
            st.write(", ".join(sorted(cmp["only_a_products"])))
        with t3:
            st.write(f"**{cmp['only_b_count']}** products bought only in {country_b}:")
            st.write(", ".join(sorted(cmp["only_b_products"])))
    else:
        st.info("Select two different countries to compare.")
