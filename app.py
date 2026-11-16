import io
import os
import pandas as pd
import numpy as np
import streamlit as st

st.set_page_config(page_title="PayInsight", page_icon="📊", layout="wide")

st.markdown("""
<style>
.main-title {font-size: 2.2rem; font-weight: 750; margin-bottom: 0.2rem;}
.sub {color:#666; margin-bottom:1.2rem;}
.metric-note {font-size:0.8rem;color:#666;}
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_data(uploaded_file):
    if uploaded_file is None:
        path = os.path.join(os.path.dirname(__file__), "data", "sample_transactions.csv")
        return pd.read_csv(path)
    return pd.read_csv(uploaded_file)

def clean_data(raw):
    df = raw.copy()
    df.columns = [str(c).strip().replace(" ", "_") for c in df.columns]
    # Flexible column mapping for common dataset names
    aliases = {
        "transaction_id": "Transaction_ID",
        "TransactionID": "Transaction_ID",
        "date": "Date",
        "transaction_date": "Date",
        "amount": "Amount_INR",
        "transaction_amount": "Amount_INR",
        "payment_method": "Payment_Method",
        "payment_type": "Payment_Method",
        "status": "Status",
        "city": "City",
        "location": "City",
        "category": "Category",
    }
    rename = {}
    for c in df.columns:
        key = c.lower()
        if key in aliases:
            rename[c] = aliases[key]
    df = df.rename(columns=rename)

    required = ["Amount_INR", "Payment_Method", "Status"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError("Required columns missing: " + ", ".join(missing))

    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Amount_INR"] = pd.to_numeric(
        df["Amount_INR"].astype(str).str.replace(",", "", regex=False)
        .str.replace("₹", "", regex=False).str.strip(),
        errors="coerce"
    )
    for c in ["Payment_Method","Status","City","Category"]:
        if c in df.columns:
            df[c] = df[c].astype("string").str.strip()
    df = df.drop_duplicates().copy()
    df = df.dropna(subset=["Amount_INR","Payment_Method","Status"])
    if "Date" in df.columns:
        df["Month"] = df["Date"].dt.strftime("%b")
        df["Month_Num"] = df["Date"].dt.month
        df["Day_Name"] = df["Date"].dt.day_name()
    df["Success_Flag"] = (df["Status"].str.lower() == "success").astype(int)
    df["Failed_Flag"] = (df["Status"].str.lower() == "failed").astype(int)
    df["Amount_Band"] = pd.cut(
        df["Amount_INR"], [0,500,2000,5000,10000,float("inf")],
        labels=["≤ ₹500","₹501–₹2K","₹2K–₹5K","₹5K–₹10K","> ₹10K"]
    )
    return df

st.markdown('<div class="main-title">📊 PayInsight</div>', unsafe_allow_html=True)
st.markdown('<div class="sub">Digital Payment Analytics Dashboard • Python + Power BI project companion</div>', unsafe_allow_html=True)

with st.sidebar:
    st.header("Data")
    uploaded = st.file_uploader("Upload CSV", type=["csv"])
    st.caption("If no file is uploaded, a clearly labeled synthetic demo dataset is used.")
    st.divider()
    st.header("Filters")

try:
    raw = load_data(uploaded)
    data = clean_data(raw)
except Exception as e:
    st.error(f"Could not process the dataset: {e}")
    st.stop()

with st.sidebar:
    if "Date" in data.columns and data["Date"].notna().any():
        min_d, max_d = data["Date"].min().date(), data["Date"].max().date()
        date_range = st.date_input("Date range", (min_d, max_d), min_value=min_d, max_value=max_d)
        if isinstance(date_range, tuple) and len(date_range) == 2:
            data = data[(data["Date"].dt.date >= date_range[0]) & (data["Date"].dt.date <= date_range[1])]
    if "Payment_Method" in data.columns:
        methods = st.multiselect("Payment method", sorted(data["Payment_Method"].dropna().unique()), default=sorted(data["Payment_Method"].dropna().unique()))
        data = data[data["Payment_Method"].isin(methods)]
    if "Status" in data.columns:
        statuses = st.multiselect("Status", sorted(data["Status"].dropna().unique()), default=sorted(data["Status"].dropna().unique()))
        data = data[data["Status"].isin(statuses)]

if data.empty:
    st.warning("No rows match the selected filters.")
    st.stop()

total_txn = len(data)
total_value = data["Amount_INR"].sum()
avg_value = data["Amount_INR"].mean()
success_rate = data["Success_Flag"].mean() * 100
failed = int(data["Failed_Flag"].sum())

c1,c2,c3,c4,c5 = st.columns(5)
c1.metric("Total Transactions", f"{total_txn:,}")
c2.metric("Total Value", f"₹{total_value:,.0f}")
c3.metric("Average Transaction", f"₹{avg_value:,.0f}")
c4.metric("Success Rate", f"{success_rate:.1f}%")
c5.metric("Failed Transactions", f"{failed:,}")

st.divider()

tab1, tab2, tab3, tab4 = st.tabs(["Overview", "Transaction Analysis", "Trends", "Data & Export"])

with tab1:
    left, right = st.columns(2)
    with left:
        st.subheader("Transaction Status")
        status_counts = data["Status"].value_counts().rename_axis("Status").reset_index(name="Transactions")
        st.bar_chart(status_counts.set_index("Status"))
    with right:
        st.subheader("Payment Method")
        method_counts = data["Payment_Method"].value_counts().rename_axis("Payment_Method").reset_index(name="Transactions")
        st.bar_chart(method_counts.set_index("Payment_Method"))
    st.subheader("Category-wise Transaction Value")
    if "Category" in data.columns:
        cat = data.groupby("Category", as_index=True)["Amount_INR"].sum().sort_values(ascending=False)
        st.bar_chart(cat)
    else:
        st.info("Category column not available in this dataset.")

with tab2:
    left, right = st.columns(2)
    with left:
        st.subheader("Average Amount by Payment Method")
        avg_method = data.groupby("Payment_Method")["Amount_INR"].mean().sort_values(ascending=False)
        st.bar_chart(avg_method)
    with right:
        st.subheader("Failed Transactions by Payment Method")
        failed_method = data[data["Status"].str.lower()=="failed"]["Payment_Method"].value_counts()
        st.bar_chart(failed_method)
    st.subheader("Amount Distribution")
    st.bar_chart(data["Amount_Band"].value_counts().sort_index())
    st.subheader("Top 10 Transactions by Amount")
    cols = [c for c in ["Transaction_ID","Date","Payment_Method","Status","City","Category","Amount_INR"] if c in data.columns]
    st.dataframe(data.sort_values("Amount_INR", ascending=False)[cols].head(10), use_container_width=True, hide_index=True)

with tab3:
    if "Date" in data.columns:
        trend = data.groupby("Date").agg(
            Transactions=("Amount_INR","size"),
            Transaction_Value=("Amount_INR","sum")
        )
        st.subheader("Daily Transaction Count")
        st.line_chart(trend["Transactions"])
        st.subheader("Daily Transaction Value")
        st.line_chart(trend["Transaction_Value"])
        month = data.groupby(["Month_Num","Month"]).agg(
            Transactions=("Amount_INR","size"),
            Value=("Amount_INR","sum")
        ).reset_index().sort_values("Month_Num")
        st.subheader("Monthly Summary")
        st.dataframe(month[["Month","Transactions","Value"]], use_container_width=True, hide_index=True)
    else:
        st.info("Date column not available.")

with tab4:
    st.subheader("Cleaned Dataset")
    st.caption(f"{len(data):,} rows after cleaning and filters.")
    st.dataframe(data.head(100), use_container_width=True, hide_index=True)
    csv_bytes = data.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Download Cleaned CSV", csv_bytes, "payinsight_cleaned.csv", "text/csv")

st.divider()
st.caption("PayInsight is an educational analytics project. The included demo data is synthetic. Replace it with an approved real/academic dataset before using project results in a final report.")
