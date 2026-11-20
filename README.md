# Online Retail Analytics Dashboard

A full-stack Python & Flask web application designed for analyzing and visualizing e-commerce transactions, customer behaviors, and product performance using core Python data structures.

Powered by the **UCI Machine Learning Online Retail Dataset** (~540,000 transactions).

---

## 🌟 Key Features

* **Interactive Dashboard**: Real-time business KPIs (Revenue, Unique Customers, Units Sold, Orders), interactive monthly revenue trend charts, top spenders, popular products, and data cleaning transparency metrics.
* **Customer Management**: Searchable customer directory with full purchase history breakdown by invoice and order timestamps.
* **Product Catalog**: Multi-criteria search and sorting by purchase frequency, units sold, and generated revenue.
* **Transaction Browser**: Granular multi-parameter filtering across country, invoice numbers, product descriptions, date ranges, and quantities.
* **Geographical Insights**: Country-level revenue rankings and set-theoretic comparisons (shared vs. exclusive products/customers across countries).

---

## 📊 Dataset Details

* **Name**: Online Retail Dataset
* **Source**: [UCI Machine Learning Repository](https://archive.ics.uci.edu/dataset/352/online+retail)
* **Timeframe**: 01/12/2010 – 09/12/2011
* **Transactions Kept**: 396,337 valid transactions (out of 541,909 raw records)
* **Attributes**: `InvoiceNo`, `StockCode`, `Description`, `Quantity`, `InvoiceDate`, `UnitPrice`, `CustomerID`, `Country`

---

## 🛠️ Tech Stack & Architecture

* **Backend**: Python 3.11, Flask
* **Frontend**: HTML5, Semantic CSS, Jinja2 Templates
* **Data Processing**: Standard Python Data Structures (`namedtuples`, `sets`, `dicts`, `lists`) for fast, memory-efficient in-memory analytics.

---

## 🚀 Run the Project Locally

1. **Clone the repository**:
   ```bash
   git clone https://github.com/SubhadeepBhandari25/Online-Retail-Dashboard.git
   cd Online-Retail-Dashboard
   ```

2. **Create and activate a virtual environment**:
   ```bash
   python -m venv venv
   # Windows:
   venv\Scripts\activate
   # macOS/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the server**:
   ```bash
   python app.py
   ```

5. **Open in browser**:
   Navigate to [http://127.0.0.1:5000](http://127.0.0.1:5000).
