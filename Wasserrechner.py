import datetime
import os
import json
import io
import streamlit as st
import plotly.graph_objects as go
from PIL import Image
from database.db import get_engine, init_db, get_session
from database.repository import (
    get_pools, get_pool, get_products,
    save_reading_for_pool, save_task, save_photo,
    complete_task_with_notes,
    get_readings_for_pool,
)
from pool_calculations.lsi import calculate_lsi, categorize_lsi
from pool_calculations.rsi import calculate_rsi, categorize_rsi
from pool_calculations.dosing import recommend_dosing_from_db
from pool_calculations.models import WaterTest

st.set_page_config(page_title="PoolPilot", page_icon="🏊", layout="centered")

engine = get_engine()
init_db(engine)
session = get_session(engine)

# Pool selector
pools = get_pools(session)
if not pools:
    st.warning("Kein Pool konfiguriert. Bitte lege unter 'Pools & Produkte' einen Pool an.")
    st.page_link("pages/01_Poolverwaltung.py", label="→ Pools & Produkte")
    st.stop()

pool_options = {p.id: f"{p.name} ({p.volume_liter} L)" for p in pools}
selected_pool_id = st.selectbox(
    "Pool", options=list(pool_options.keys()),
    format_func=lambda x: pool_options[x],
    key="pool_selector",
)
pool = get_pool(session, selected_pool_id)

# Load products for dosing
products = get_products(session)

# Load trinkwasser defaults if linked
tw_defaults = {"alkalinity": 100, "hardness": 200}
if pool.trinkwasser_id:
    from database.repository import get_trinkwasser
    tw = get_trinkwasser(session, pool.trinkwasser_id)
    if tw:
        tw_defaults = {"alkalinity": tw.alkalinity_default,
                       "hardness": tw.calcium_hardness_default}

st.title("🏊 PoolPilot")
st.caption(f"{pool.name} · {pool.volume_liter} Liter · {pool.pool_type}")

st.divider()

# Initialize session state
if "last_dosing" not in st.session_state:
    st.session_state.last_dosing = []
if "task_created" not in st.session_state:
    st.session_state.task_created = False

# Step 1: Measurement input with live calculation
st.subheader("1️⃣ Messwerte erfassen")

help_texts = {
    "ph": "Der pH-Wert beeinflusst Chlorwirkung und Wasserbalance. "
          "Teststreifen messen von 6,2 bis 8,4. Ziel: 7,2–7,6.",
    "chlorine": "Freies Chlor in mg/L. "
                "Teststreifen messen freies Chlor. Ziel: 0,5–3,0 mg/L.",
    "temp": "Wassertemperatur in °C. Beeinflusst LSI/RSI direkt.",
    "alk": "Säurepufferkapazität (mg/L CaCO₃). "
           "Verhindert pH-Schwankungen. Wird NICHT mit Teststreifen gemessen. "
           "Trinkwasser-Default: {} mg/L".format(tw_defaults["alkalinity"]),
    "hard": "Calcium-Ionen (mg/L CaCO₃, NICHT Gesamthärte). "
            "Wichtig für LSI-Berechnung. Wird NICHT mit Teststreifen gemessen. "
            "Trinkwasser-Default: {} mg/L".format(tw_defaults["hardness"]),
}

col1, col2 = st.columns(2)

with col1:
    ph = st.slider("pH-Wert ⓘ", 6.2, 8.4, 7.4, 0.1,
                    help=help_texts["ph"])
    chlorine = st.slider("Chlor (mg/L) ⓘ", 0.0, 10.0, 1.5, 0.1,
                          help=help_texts["chlorine"])
    temperature = st.slider("Wassertemperatur (°C) ⓘ", 0, 45,
                              int(pool.temperature_default), 1,
                              help=help_texts["temp"])

with col2:
    alkalinity = st.slider("Alkalinität (mg/L CaCO₃) ⓘ", 0, 500,
                             int(tw_defaults["alkalinity"]), 10,
                             help=help_texts["alk"])
    hardness = st.slider("Calciumhärte (mg/L CaCO₃) ⓘ", 0, 500,
                           int(tw_defaults["hardness"]), 10,
                           help=help_texts["hard"])
    notes = st.text_input("📝 Notizen (optional)", placeholder="z. B. Wetter, Wasserstand...")

# Live calculation
lsi = calculate_lsi(ph, temperature, hardness, alkalinity)
rsi = calculate_rsi(ph, temperature, hardness, alkalinity)
lsi_cat = categorize_lsi(lsi)
rsi_cat = categorize_rsi(rsi)

test = WaterTest(ph=ph, chlorine=chlorine, alkalinity=alkalinity,
                 hardness=hardness, temperature_c=temperature)
dosing = recommend_dosing_from_db(test, pool, products)

st.divider()

# Step 2: Results display (auto-updated)
st.subheader("2️⃣ Wasserbalance")

col_lsi, col_rsi, col_status = st.columns(3)

with col_lsi:
    lsi_color = "green" if lsi_cat == "ausgeglichen" else ("red" if lsi_cat == "korrosiv" else "orange")
    st.markdown(f"### LSI: <span style='color:{lsi_color}'>{lsi:+.2f}</span>",
                unsafe_allow_html=True)
    st.caption(f"→ {lsi_cat}")

with col_rsi:
    st.markdown(f"### RSI: {rsi:.1f}")
    st.caption(f"→ {rsi_cat}")

with col_status:
    if lsi_cat == "ausgeglichen" and rsi_cat == "neutral":
        st.success("✅ Wasser im Gleichgewicht")
    else:
        st.warning("⚡ Handlungsbedarf")

# Plotly gauge
gauge_fig = go.Figure()
gauge_fig.add_trace(go.Indicator(
    mode="gauge+number",
    value=lsi,
    title={"text": "LSI – Live"},
    gauge={
        "axis": {"range": [-2, 2]},
        "bar": {"color": "darkblue"},
        "steps": [
            {"range": [-2, -0.5], "color": "red"},
            {"range": [-0.5, 0.5], "color": "green"},
            {"range": [0.5, 2], "color": "orange"},
        ],
    },
))
st.plotly_chart(gauge_fig, use_container_width=True)

# pH / Chlor leiste
ph_ok = pool.ph_min <= ph <= pool.ph_max
chl_ok = pool.chlorine_min <= chlorine <= pool.chlorine_max
col_a, col_b = st.columns(2)
col_a.metric("pH", f"{ph:.1f}", delta="✅ i.O." if ph_ok else f"⚠️ Ziel {pool.ph_min}–{pool.ph_max}")
col_b.metric("Chlor", f"{chlorine:.1f} mg/L", delta="✅ i.O." if chl_ok else f"⚠️ Ziel {pool.chlorine_min}–{pool.chlorine_max}")

st.divider()

# Step 3: Dosing recommendations
st.subheader("3️⃣ Dosierempfehlung")

if dosing:
    for d in dosing:
        with st.container(border=True):
            col_a, col_b = st.columns([3, 1])
            with col_a:
                st.warning(f"**{d.product}**: {d.amount:g} {d.unit}")
                st.caption(d.reason)
            with col_b:
                if st.button("📋 Aufgabe", key=f"task_{d.product}_{d.amount}", use_container_width=True):
                    save_task(
                        session,
                        task_type="dosierung",
                        title=f"{d.product}: {d.amount:g} {d.unit}",
                        description=d.reason,
                        due_date=datetime.date.today(),
                        interval_days=0,
                    )
                    st.session_state.task_created = True
                    st.rerun()

        # Step 4: Execution documentation
        st.caption("Ausführung dokumentieren:")
        exec_col1, exec_col2 = st.columns([3, 1])
        with exec_col1:
            exec_notes = st.text_input(
                "Was wurde gemacht?",
                placeholder=f"z. B. {d.amount:g} {d.unit} zugegeben um ...",
                key=f"exec_{d.product}",
            )
        with exec_col2:
            if st.button("✅ Erledigt", key=f"done_{d.product}", use_container_width=True):
                task_data = {
                    "date": datetime.date.today().isoformat(),
                    "time": datetime.datetime.now().strftime("%H:%M"),
                    "action": exec_notes or f"{d.amount:g} {d.unit} zugegeben",
                    "product": d.product,
                    "amount": d.amount,
                    "unit": d.unit,
                    "reason": d.reason,
                }
                if "executed_actions" not in st.session_state:
                    st.session_state.executed_actions = []
                st.session_state.executed_actions.append(task_data)

                if d.follow_up_days > 0:
                    save_task(
                        session,
                        task_type="nachkontrolle",
                        title=f"{d.product} – Nachkontrolle",
                        description=f"Folgeaufgabe in {d.follow_up_days} Tagen "
                                    f"(automatisch erzeugt am {datetime.date.today().isoformat()})",
                        due_date=datetime.date.today() + datetime.timedelta(days=d.follow_up_days),
                        interval_days=d.follow_up_days,
                    )
                st.rerun()
else:
    st.success("✅ Keine Dosierung erforderlich — alle Werte im Zielbereich.")

st.divider()

# Photo section
st.subheader("📸 Foto")
photo_source = st.radio("Foto-Quelle", ["📁 Hochladen", "📸 Kamera"],
                        horizontal=True, label_visibility="collapsed")
uploaded_file = None
camera_file = None
if photo_source == "📸 Kamera":
    camera_file = st.camera_input("📸 Mit Kamera aufnehmen")
else:
    uploaded_file = st.file_uploader("📁 Vom Gerät hochladen", type=["jpg", "jpeg", "png"])

photo_path = None
photo_data = None
if camera_file:
    photo_data = camera_file.getvalue()
    img = Image.open(io.BytesIO(photo_data))
    photo_dir = os.path.join(os.path.dirname(__file__), "data", "photos")
    os.makedirs(photo_dir, exist_ok=True)
    fname = f"reading_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    photo_path = os.path.join(photo_dir, fname)
    img.save(photo_path)
    st.image(photo_data, caption="Kamera-Aufnahme", width=300)
elif uploaded_file:
    photo_data = uploaded_file.getvalue()
    img = Image.open(uploaded_file)
    photo_dir = os.path.join(os.path.dirname(__file__), "data", "photos")
    os.makedirs(photo_dir, exist_ok=True)
    fname = f"reading_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    photo_path = os.path.join(photo_dir, fname)
    img.save(photo_path)
    st.image(photo_data, caption="Hochgeladenes Foto", width=300)

st.divider()

# Save button
if st.button("💾 Messung speichern", type="primary", use_container_width=True):
    dosing_data = [{"product": d.product, "amount": d.amount, "unit": d.unit, "reason": d.reason}
                   for d in dosing] if dosing else []

    reading = save_reading_for_pool(
        session, pool_id=selected_pool_id,
        ph=ph, chlorine=chlorine, alkalinity=alkalinity, hardness=hardness,
        temperature_c=temperature, lsi=lsi, rsi=rsi,
        dosing=dosing_data, notes=notes,
    )

    # Link photo if taken
    if photo_path:
        save_photo(session, image_path=photo_path,
                   caption=f"Messung {datetime.datetime.now().strftime('%d.%m.%Y %H:%M')}")

    # Create tasks for dosing if not already done
    if not st.session_state.get("task_created"):
        for d in dosing:
            save_task(
                session,
                task_type="dosierung",
                title=f"{d.product}: {d.amount:g} {d.unit}",
                description=d.reason,
                due_date=datetime.date.today(),
                interval_days=0,
            )

    st.success("✅ Messung gespeichert!")
    st.session_state.last_dosing = dosing
    st.session_state.task_created = False
    if "executed_actions" in st.session_state:
        del st.session_state.executed_actions

# Show last saved result
if st.session_state.last_dosing:
    with st.expander("Letzte gespeicherte Messung"):
        st.json([{"product": d.product, "amount": d.amount, "unit": d.unit, "reason": d.reason}
                 for d in st.session_state.last_dosing])
