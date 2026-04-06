import streamlit as st

st.title("📦 Inventory Decision Engine")

uploaded_file = st.file_uploader("Upload PDF", type="pdf")

if uploaded_file:
    st.success("File berhasil diupload")

    if st.button("🔍 Analyze"):
        st.write("🚀 App berjalan normal")

        # TEST: baca file sebagai binary
        try:
            file_bytes = uploaded_file.read()
            st.write(f"Ukuran file: {len(file_bytes)} bytes")
            st.success("File bisa dibaca ✅")
        except Exception as e:
            st.error(f"Error baca file: {e}")
