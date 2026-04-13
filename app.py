import streamlit as st
import pandas as pd
import numpy as np
import re
from datetime import datetime
from fpdf import FPDF

st.set_page_config(page_title="Smart Inventory AI", layout="wide")

st.title("🧠 Smart Inventory Decision Engine")

# =========================
# ⚙️ SETTINGS
# =========================
st.sidebar.header("⚙️ Parameter")

lead_time = st.sidebar.number_input("Lead Time (hari)", value=14)
review_period = st.sidebar.number_input("Review Period (hari)", value=7)
buffer_days = st.sidebar.number_input("Buffer (hari)", value=3)
MOQ = st.sidebar.number_input("MOQ (minimum order)", value=5)

TARGET_DOI = lead_time + review_period + buffer_days

# =========================
# 📂 FILE UPLOAD
# =========================
uploaded_file = st.file_uploader("Upload Excel Accurate", type=["xlsx"])

# =========================
# 📅 AUTO DETECT DATE
# =========================
def extract_date_range(file):
    df_raw = pd.read_excel(file, header=None)
    text_blob = " ".join(df_raw.astype(str).values.flatten())

    match = re.search(
        r"Dari\s+(\d{2}\s\w+\s\d{4})\s+s/d\s+(\d{2}\s\w+\s\d{4})",
        text_blob
    )

    if match:
        start_str, end_str = match.groups()
        start_date = datetime.strptime(start_str, "%d %b %Y")
        end_date = datetime.strptime(end_str, "%d %b %Y")
        days = (end_date - start_date).days + 1
        return days
    return None

# =========================
# 📊 LOAD DATA
# =========================
def load_excel(file):
    df = pd.read_excel(file)
    df.columns = [col.lower().strip() for col in df.columns]
    return df

# =========================
# 🧠 CORE ENGINE
# =========================
def calculate(df, days):

    # ===== DEMAND =====
    df["ads"] = df["keluar"] / days
    df["ads"] = df["ads"].clip(lower=0.01)

    # ===== STOCK =====
    df["stock"] = df["stock akhir"]

    # ===== DOI =====
    df["doi"] = df["stock"] / df["ads"]

    # ===== CLASSIFICATION =====
    def classify(row):
        if row["ads"] > 5:
            return "FAST"
        elif row["ads"] > 1:
            return "MEDIUM"
        elif row["ads"] > 0.1:
            return "SLOW"
        else:
            return "DEAD"

    df["class"] = df.apply(classify, axis=1)

    # ===== STOCKOUT FLAG =====
    df["stockout"] = df["stock"] == 0

    # ===== STATUS =====
    def get_status(row):
        if row["doi"] < lead_time:
            return "CRITICAL"
        elif row["doi"] < TARGET_DOI:
            return "REORDER"
        elif row["doi"] > 60:
            return "OVERSTOCK"
        else:
            return "OK"

    df["status"] = df.apply(get_status, axis=1)

    # ===== ORDER QTY =====
    def calc_order(row):
        if row["status"] in ["CRITICAL", "REORDER"]:
            raw = (TARGET_DOI - row["doi"]) * row["ads"]
            order = max(MOQ, round(raw))
            return order
        return 0

    df["reorder_qty"] = df.apply(calc_order, axis=1)

    # ===== PRIORITY =====
    df["priority"] = (1 / df["doi"]) * 0.6 + df["ads"] * 0.4
    df = df.sort_values(by="priority", ascending=False)

    return df

# =========================
# 📄 PDF OUTPUT
# =========================
def generate_pdf(df):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=9)

    pdf.cell(200, 10, txt="Smart Reorder Report", ln=True)

    for _, row in df.iterrows():
        if row["status"] in ["CRITICAL", "REORDER"]:
            line = f"{row['nama barang']} | {row['class']} | DOI:{round(row['doi'],1)} | Order:{row['reorder_qty']}"
            pdf.cell(200, 7, txt=line, ln=True)

    file_path = "reorder_report.pdf"
    pdf.output(file_path)
    return file_path

# =========================
# 🚀 RUN
# =========================
if uploaded_file:

    days = extract_date_range(uploaded_file)

    if not days:
        st.warning("⚠️ Periode tidak terbaca, input manual")
        days = st.number_input("Masukkan jumlah hari", value=7)

    st.success(f"📅 Periode terbaca: {days} hari")

    df = load_excel(uploaded_file)

    required = ["nama barang", "stock awal", "masuk", "keluar", "stock akhir"]
    missing = [col for col in required if col not in df.columns]

    if missing:
        st.error(f"❌ Kolom tidak lengkap: {missing}")
    else:
        result = calculate(df, days)

        # METRICS
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("🚨 Critical", (result["status"] == "CRITICAL").sum())
        col2.metric("📦 Reorder", (result["status"] == "REORDER").sum())
        col3.metric("📉 Overstock", (result["status"] == "OVERSTOCK").sum())
        col4.metric("💀 Dead Stock", (result["class"] == "DEAD").sum())

        st.subheader("🔥 Priority Order List")
        st.dataframe(result.head(50))

        st.subheader("📊 Full Data")
        st.dataframe(result)

        pdf_file = generate_pdf(result)

        with open(pdf_file, "rb") as f:
            st.download_button("📄 Download Report", f)
