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
# 📅 DATE NORMALIZER
# =========================
MONTH_MAP = {
    "Jan": "Jan", "Feb": "Feb", "Mar": "Mar", "Apr": "Apr",
    "Mei": "May", "Jun": "Jun", "Jul": "Jul", "Agu": "Aug",
    "Sep": "Sep", "Okt": "Oct", "Nov": "Nov", "Des": "Dec",
    "April": "Apr"
}

def normalize_date(text):
    for indo, eng in MONTH_MAP.items():
        text = text.replace(indo, eng)
    return text

def extract_date_range(file):
    try:
        df_raw = pd.read_excel(file, header=None, nrows=10)

        text_lines = []
        for row in df_raw.values:
            row_text = " ".join([str(cell) for cell in row if pd.notna(cell)])
            text_lines.append(row_text)

        text_blob = " ".join(text_lines)

        match = re.search(
            r"Dari\s+(\d{2}\s\w+\s\d{4})\s+s/d\s+(\d{2}\s\w+\s\d{4})",
            text_blob
        )

        if match:
            start_str, end_str = match.groups()

            start_str = normalize_date(start_str)
            end_str = normalize_date(end_str)

            start_date = datetime.strptime(start_str, "%d %b %Y")
            end_date = datetime.strptime(end_str, "%d %b %Y")

            days = (end_date - start_date).days + 1
            return days

    except Exception as e:
        st.warning(f"Gagal baca periode: {e}")

    return None

# =========================
# 📊 LOAD + AUTO DETECT HEADER
# =========================
def load_excel(file):
    df_raw = pd.read_excel(file, header=None)

    # Cari baris header (yang ada kata "nama" & "akhir")
    header_row = None
    for i, row in df_raw.iterrows():
        row_str = " ".join([str(x).lower() for x in row])
        if "nama" in row_str and ("akhir" in row_str or "saldo" in row_str):
            header_row = i
            break

    if header_row is None:
        st.error("❌ Tidak menemukan header tabel")
        return None

    df = pd.read_excel(file, header=header_row)
    df.columns = [col.lower().strip() for col in df.columns]

    # =========================
    # AUTO MAPPING KOLOM
    # =========================
    col_map = {}

    for col in df.columns:
        if "nama" in col:
            col_map[col] = "nama barang"
        elif "awal" in col:
            col_map[col] = "stock awal"
        elif "masuk" in col:
            col_map[col] = "masuk"
        elif "keluar" in col or "out" in col:
            col_map[col] = "keluar"
        elif "akhir" in col or "saldo" in col:
            col_map[col] = "stock akhir"

    df = df.rename(columns=col_map)

    return df

# =========================
# 🧠 CORE ENGINE
# =========================
def calculate(df, days):

    df["ads"] = df["keluar"] / days
    df["ads"] = df["ads"].clip(lower=0.01)

    df["stock"] = df["stock akhir"]
    df["doi"] = df["stock"] / df["ads"]

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

    def calc_order(row):
        if row["status"] in ["CRITICAL", "REORDER"]:
            raw = (TARGET_DOI - row["doi"]) * row["ads"]
            return max(MOQ, round(raw))
        return 0

    df["reorder_qty"] = df.apply(calc_order, axis=1)

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

    st.success(f"📅 Periode digunakan: {days} hari")

    df = load_excel(uploaded_file)

    if df is not None:
        st.write("🔍 Kolom terbaca:", df.columns.tolist())

        required = ["nama barang", "stock awal", "masuk", "keluar", "stock akhir"]
        missing = [col for col in required if col not in df.columns]

        if missing:
            st.error(f"❌ Kolom belum lengkap: {missing}")
        else:
            result = calculate(df, days)

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
