import streamlit as st
from pathlib import Path
from datetime import date
from utils.export_import import create_export_zip

st.set_page_config(page_title="Data Export / Import", page_icon="🔐")

DATA_DIR = Path(__file__).parent.parent / "data"

st.title("🔐 Data Export / Import")

st.header("Export")
st.write("Download a complete ZIP archive of the database and all photos.")

if st.button("📦 Download full backup (ZIP)"):
    with st.spinner("Creating backup..."):
        zip_bytes = create_export_zip(DATA_DIR)
    st.download_button(
        label="💾 Save ZIP",
        data=zip_bytes,
        file_name=f"poolpilot-backup-{date.today().isoformat()}.zip",
        mime="application/zip",
    )
