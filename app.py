import streamlit as st
import pandas as pd
import pdfplumber

st.title("📦 Inventory Decision Engine")

uploaded_file = st.file_uploader("Upload PDF Accurate", type="pdf")

if uploaded_file:
    data = []

    with pdfplumber.open(uploaded_file) as pdf:
        for page in pdf.pages:
            table = page.extract_table()
            if table:
                for row in table[1:]:
                    try:
                        nama = row[0]
                        kode = row[1]
                        keluar = float(str(row[6]).replace(",", "").replace(".", ""))
                        stok = float(str(row[8]).replace(",", "").replace(".", ""))

                        data.append([nama, kode, keluar, stok])
                    except:
                        continue

    df = pd.DataFrame(data, columns=["Nama", "Kode", "Keluar", "Stok"])

    DAYS = 94
    SAFETY = 14

    def lead_time(nama):
        return 5 if "TH" in str(nama) else 14

    df = df[df["Keluar"] > 2]
    df = df[df["Stok"] > 0]

    df["AvgDaily"] = df["Keluar"] / DAYS
    df["LeadTime"] = df["Nama"].apply(lead_time)
    df["DOI"] = df["Stok"] / df["AvgDaily"]
    df["Target"] = (df["LeadTime"] + SAFETY) * df["AvgDaily"]
    df["QtyBeli"] = df["Target"] - df["Stok"]

    def kategori(row):
        if row["DOI"] < row["LeadTime"]:
            return "🔴 BELI SEKARANG"
        elif row["DOI"] < (row["LeadTime"] + SAFETY):
            return "🟠 BELI"
        else:
            return "🟡 AMAN"

    df["Status"] = df.apply(kategori, axis=1)
    df["QtyBeli"] = df["QtyBeli"].apply(lambda x: max(0, round(x)))

    st.dataframe(df.sort_values(by="QtyBeli", ascending=False))
