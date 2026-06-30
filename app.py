import streamlit as st
from database.db import get_engine, init_db, get_session
from database.repository import get_latest_reading, get_pending_tasks
from utils.config_loader import load_config

st.set_page_config(page_title="Pool Wasser-Gleichgewicht", page_icon="💧", layout="centered")

engine = get_engine()
init_db(engine)

config = load_config()
session = get_session(engine)

st.title("💧 Pool Wasser-Gleichgewicht")
st.caption(f"🔵 {config.name} · {config.volume_liter} Liter")

col1, col2 = st.columns(2)
with col1:
    latest = get_latest_reading(session)
    if latest:
        st.metric("Letzte Messung", latest.timestamp.strftime("%d.%m.%Y %H:%M"))
        st.metric("pH", f"{latest.ph:.1f}")
        st.metric("Chlor", f"{latest.chlorine:.1f} mg/L")
    else:
        st.info("Noch keine Messungen erfasst.")

with col2:
    if latest:
        st.metric("LSI", f"{latest.lsi_value:+.2f}")
        st.metric("RSI", f"{latest.rsi_value:.1f}")
    else:
        st.write("")

st.divider()
st.subheader("📋 Wartung")
tasks = get_pending_tasks(session)
if tasks:
    for task in tasks:
        st.write(f"- {task.title}")
else:
    st.success("Keine offenen Aufgaben")

st.divider()
st.page_link("pages/1_Wasserrechner.py", label="🔬 Neue Messung & Berechnung", use_container_width=True)
