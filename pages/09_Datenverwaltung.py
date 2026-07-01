import streamlit as st
from pathlib import Path
from datetime import date
from utils.export_import import create_export_zip, analyze_zip

st.set_page_config(page_title="Daten-Export / -Import", page_icon="🔐")

DATA_DIR = Path(__file__).parent.parent / "data"

# Initialize session state
if "export_zip_bytes" not in st.session_state:
    st.session_state.export_zip_bytes = None
if "analyze_result" not in st.session_state:
    st.session_state.analyze_result = None
if "import_zip_bytes" not in st.session_state:
    st.session_state.import_zip_bytes = None

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
            st.session_state.export_zip_bytes = zip_bytes
        except Exception as e:
            st.error(f"Backup fehlgeschlagen: {e}")

if st.session_state.export_zip_bytes:
    st.download_button(
        label="💾 ZIP speichern",
        data=st.session_state.export_zip_bytes,
        file_name=f"poolpilot-backup-{date.today().isoformat()}.zip",
        mime="application/zip",
    )
    if st.button("Neues Backup erstellen"):
        st.session_state.export_zip_bytes = None

st.header("Import")
st.write("Lade ein Backup-ZIP hoch, um Daten in die aktuelle Datenbank zu importieren oder zusammenzuführen.")

uploaded_zip = st.file_uploader("⬆ Backup-ZIP hochladen", type="zip")

if uploaded_zip is not None:
    zip_bytes = uploaded_zip.getvalue()

    if st.button("🔍 ZIP analysieren"):
        with st.spinner("Analysiere..."):
            try:
                result = analyze_zip(zip_bytes)
            except Exception as e:
                st.error(f"Analyse fehlgeschlagen: {e}")
                st.stop()
        if not result.valid:
            st.error(f"Ungültiges ZIP: {result.error}")
            st.stop()
        st.success("ZIP-Analyse abgeschlossen!")

        st.session_state.analyze_result = result
        st.session_state.import_zip_bytes = zip_bytes

        col1, col2 = st.columns(2)
        col1.metric("Datenbank-Einträge", sum(result.counts.values()))
        col2.metric("Fotos", result.photo_count)

        st.subheader("Gefundene Daten")
        for key, label in [
            ("pools", "Pools"), ("products", "Produkte"),
            ("instruments", "Instrumente"), ("trinkwasser", "Trinkwasser-Quellen"),
            ("task_templates", "Aufgaben-Vorlagen"),
            ("readings", "Messwerte"), ("maintenance_tasks", "Aufgaben"),
        ]:
            c = result.counts.get(key, 0)
            if c > 0:
                st.write(f"- {label}: **{c}**")

if st.session_state.analyze_result:
    pass
