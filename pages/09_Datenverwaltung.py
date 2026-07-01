import streamlit as st
from pathlib import Path
from datetime import date
from utils.export_import import create_export_zip

st.set_page_config(page_title="Daten-Export / -Import", page_icon="🔐")

DATA_DIR = Path(__file__).parent.parent / "data"

st.title("🔐 Daten-Export / -Import")

st.header("Export")
st.write("Lade ein ZIP-Archiv mit der gesamten Datenbank und allen Fotos herunter.")

if st.button("📦 Vollständiges Backup erstellen"):
    if not DATA_DIR.exists():
        st.error(f"Der Datenordner {DATA_DIR} existiert nicht.")
        st.stop()
    with st.spinner("Backup wird erstellt..."):
        try:
            zip_bytes = create_export_zip(DATA_DIR)
            st.session_state.zip_bytes = zip_bytes
        except Exception as e:
            st.error(f"Backup fehlgeschlagen: {e}")

if st.session_state.get("zip_bytes"):
    st.download_button(
        label="💾 ZIP speichern",
        data=st.session_state.zip_bytes,
        file_name=f"poolpilot-backup-{date.today().isoformat()}.zip",
        mime="application/zip",
    )
    if st.button("Neues Backup erstellen"):
        st.session_state.zip_bytes = None
        st.rerun()
