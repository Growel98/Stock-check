import streamlit as st
import pandas as pd
import pdfplumber

st.set_page_config(page_title="Inventory Decision Engine", layout="wide")

st.title("📦 Inventory Decision Engine")
st.write("Upload laporan PDF dari Accurate untuk analisa restock")

uploaded_file = st.file_uploader("Upload PDF Accurate", type="pdf")

# PARAMETER BISNIS
DAYS = 94
SAFETY = 14

def lead_time(nama):
    return 5 if "TH" in str(nama) else 14

if uploaded_file:
    st.success("File berhasil diupload ✅")

    if st.button("🔍 Analyze Sekarang"):
        st.write("🚀 Memulai analisa...")

        data = []

        try:
            with pdfplumber.open(uploaded_file) as pdf:
                st.write(f"📄 Total halaman: {len(pdf.pages)}")

                for i, page in enumerate(pdf.pages):
                    table = page.extract_table()

                    if table:
                        st.write(f"✅ Halaman {i+1}: table ditemukan")

                        for row in table[1:]:
                            try:
                                nama = row[0]
                                kode = row[1]

                                keluar = float(
                                    str(row[6]).replace(",", "").replace(".", "")
                                )

                                stok = float(
                                    str(row[8]).replace(",", "").replace(".", "")
                                )

                                data.append([nama, kode, keluar, stok])

                            except:
                                continue
                    else:
                        st.write(f"❌ Halaman {i+1}: tidak ada table")

        except Exception as e:
            st.error(f"Gagal membaca PDF: {e}")

        st.write(f"📊 Total data terbaca: {len(data)}")

        # =========================
        # JIKA DATA KOSONG
        # =========================
        if len(data) == 0:
            st.error("❌ Tidak ada data yang berhasil dibaca dari PDF")
            st.warning("Kemungkinan format PDF tidak terbaca sebagai table")

        else:
            df = pd.DataFrame(data, columns=["Nama", "Kode", "Keluar", "Stok"])

            # FILTER
            df = df[df["Keluar"] > 2]
            df = df[df["Stok"] > 0]

            if len(df) == 0:
                st.warning("⚠️ Data ada, tapi setelah filter tidak tersisa")

            else:
                # =========================
                # HITUNG METRIK
                # =========================
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

                # =========================
                # OUTPUT
                # =========================
                st.success("🔥 Analisa selesai")

                # PRIORITAS
                st.subheader("🔴 Prioritas Restock")
                prioritas = df[df["Status"] != "🟡 AMAN"].sort_values(
                    by="QtyBeli", ascending=False
                )
                st.dataframe(prioritas, use_container_width=True)

                # SEMUA DATA
                st.subheader("📦 Semua SKU")
                st.dataframe(
                    df.sort_values(by="QtyBeli", ascending=False),
                    use_container_width=True
                )
