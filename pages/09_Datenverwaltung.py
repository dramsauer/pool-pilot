import streamlit as st
from pathlib import Path
from datetime import date
from utils.export_import import create_export_zip, analyze_zip, execute_import
from database.db import get_session
from database.models import Pool, Product, Instrument, Trinkwasser, TaskTemplate, Reading, MaintenanceTask
from utils.theme import inject_theme

st.set_page_config(page_title="Daten-Export / -Import", page_icon="🔐")
inject_theme()

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
    result = st.session_state.analyze_result
    data_dir = DATA_DIR

    st.subheader("Import-Optionen")
    st.write("Wähle für jede Kategorie, wie verfahren werden soll:")

    current_session = get_session()
    current_counts = {
        "pools": current_session.query(Pool).count(),
        "products": current_session.query(Product).count(),
        "instruments": current_session.query(Instrument).count(),
        "trinkwasser": current_session.query(Trinkwasser).count(),
        "task_templates": current_session.query(TaskTemplate).count(),
        "readings": current_session.query(Reading).count(),
        "maintenance_tasks": current_session.query(MaintenanceTask).count(),
    }
    current_session.close()

    strategies = {}
    cols = st.columns([3, 1, 1, 2])
    cols[0].markdown("**Kategorie**")
    cols[1].markdown("**Aktuell**")
    cols[2].markdown("**Import**")
    cols[3].markdown("**Aktion**")

    for key, label in [
        ("pools", "Pools"),
        ("products", "Produkte"),
        ("instruments", "Instrumente"),
        ("trinkwasser", "Trinkwasser-Quellen"),
        ("task_templates", "Aufgaben-Vorlagen"),
        ("readings", "Messwerte"),
        ("maintenance_tasks", "Aufgaben"),
    ]:
        imported_count = result.counts.get(key, 0)
        if imported_count == 0:
            continue

        cols = st.columns([3, 1, 1, 2])
        cols[0].write(label)
        cols[1].write(str(current_counts.get(key, 0)))
        cols[2].write(str(imported_count))
        strategy = cols[3].selectbox(
            "", ["merge", "replace", "skip"],
            index=0,
            key=f"strategy_{key}",
            label_visibility="collapsed",
        )
        strategies[key] = strategy

    # Dependency warnings
    from utils.export_import import PARENT_DEPENDENCIES
    warnings = []
    for child, parents in PARENT_DEPENDENCIES.items():
        if child not in ["readings", "maintenance_tasks"]:
            continue
        if strategies.get(child, "skip") != "skip":
            for parent in parents:
                if strategies.get(parent, "skip") == "skip":
                    warnings.append(
                        f"⚠️ **{child}** erfordert **{parent}**. "
                        f"Bitte ändere '{parent}' von 'Überspringen' zu 'Zusammenführen' oder 'Ersetzen'."
                    )

    if warnings:
        for w in warnings:
            st.warning(w)
        st.session_state["import_blocked"] = True
    else:
        st.session_state["import_blocked"] = False

    # Confirmation + Execute
    if "confirm_import" not in st.session_state:
        st.session_state["confirm_import"] = False

    if st.button("🚀 Import durchführen", disabled=st.session_state.get("import_blocked", True)):
        st.session_state["confirm_import"] = True

    if st.session_state["confirm_import"] and not st.session_state.get("import_blocked", True):
        st.warning("Dieser Vorgang verändert die Datenbank. Fortfahren?")
        col1, col2 = st.columns(2)
        if col1.button("✅ Ja, importieren"):
            with st.spinner("Importiere Daten..."):
                session = get_session()
                try:
                    import_result = execute_import(
                        current_session=session,
                        imported_db_path=result.imported_db_path,
                        strategies=strategies,
                        id_maps={},
                        photos_extract_dir=result.extract_dir,
                        data_photos_dir=str(data_dir / "photos"),
                    )
                    st.success("Import abgeschlossen!")
                    st.subheader("Ergebnis")

                    from utils.export_import import DEPENDENCY_ORDER
                    for cat in DEPENDENCY_ORDER:
                        if cat in import_result:
                            r = import_result[cat]
                            if r["status"] == "ok":
                                st.success(f"✅ {cat}: {r['count']} Datensätze {r['action']}")
                            elif r["status"] == "skipped":
                                st.info(f"⏭️ {cat}: übersprungen")

                    if "photo_files" in import_result:
                        pr = import_result["photo_files"]
                        if pr["status"] == "ok":
                            st.success(f"✅ Fotodateien: {pr['count']} Dateien {pr['action']}")

                except Exception as e:
                    st.error(f"Import fehlgeschlagen: {e}")
                finally:
                    session.close()

            # Clean up temp dir
            import shutil
            if result.tmp_path:
                shutil.rmtree(result.tmp_path, ignore_errors=True)

            st.session_state["confirm_import"] = False
            st.session_state["analyze_result"] = None

        if col2.button("❌ Abbrechen"):
            st.session_state["confirm_import"] = False
