import streamlit as st
import pandas as pd

st.set_page_config(page_title="Inventory Decision Engine", layout="wide")

st.title("📦 Inventory Decision Engine")

uploaded_file = st.file_uploader("Upload PDF Accurate", type="pdf")

if uploaded_file:
    st.success("File berhasil diupload ✅")

    if st.button("🔍 Analyze Sekarang"):
        st.write("🚀 Memulai analisa...")

        try:
            import pdfplumber

            data = []

            with pdfplumber.open(uploaded_file) as pdf:
                st.write(f"📄 Total halaman: {len(pdf.pages)}")

                for i, page in enumerate(pdf.pages):
                    table = page.extract_table()

                    if table:
                        st.write(f"✅ Halaman {i+1}: table ditemukan")

                        for row in table[1:]:
                            try:
                                if len(row) < 9:
                                    continue

                                nama = row[0]
                                kode = row[1]

                                keluar = float(str(row[6]).replace(",", "").replace(".", ""))
                                stok = float(str(row[8]).replace(",", "").replace(".", ""))

                                data.append([nama, kode, keluar, stok])

                            except Exception as e:
                                continue
                    else:
                        st.write(f"❌ Halaman {i+1}: tidak ada table")

            st.write(f"📊 Total data terbaca: {len(data)}")

            if len(data) == 0:
                st.error("❌ Tidak ada data terbaca dari PDF")
            else:
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

                st.success("🔥 Analisa selesai")

                st.dataframe(df.sort_values(by="QtyBeli", ascending=False))

        except Exception as e:
            st.error(f"💥 Terjadi error: {e}")
            st.warning("Cek format PDF atau dependencies")
