import streamlit as st
import plotly.graph_objects as go
from database.db import get_engine, init_db, get_session
from database.repository import save_reading
from pool_calculations.lsi import calculate_lsi, categorize_lsi
from pool_calculations.rsi import calculate_rsi, categorize_rsi
from pool_calculations.dosing import recommend_dosing
from pool_calculations.models import WaterTest
from utils.config_loader import load_config

st.set_page_config(page_title="Wasserrechner", page_icon="🔬")

engine = get_engine()
init_db(engine)
session = get_session(engine)
config = load_config()

st.title("🔬 Wasserrechner & Dosierung")
st.caption(f"Pool: {config.name} ({config.volume_liter} L)")

with st.form("messung"):
    col1, col2 = st.columns(2)
    with col1:
        ph = st.slider("pH-Wert", 6.2, 8.4, 7.4, 0.1)
        chlorine = st.slider("Chlor (mg/L)", 0.0, 10.0, 1.5, 0.5)
        alkalinity = st.slider("Alkalinität (mg/L CaCO₃)", 0, 300, 100, 10)
    with col2:
        hardness = st.slider("Calciumhärte (mg/L CaCO₃)", 0, 500, 200, 10)
        temperature = st.slider("Wassertemperatur (°C)", 0, 45, config.temperature_default, 1)
        notes = st.text_input("Notizen")
    submitted = st.form_submit_button("Berechnen & Speichern", type="primary", use_container_width=True)

    if submitted:
        lsi = calculate_lsi(ph, temperature, hardness, alkalinity)
        rsi = calculate_rsi(ph, temperature, hardness, alkalinity)
        lsi_cat = categorize_lsi(lsi)
        rsi_cat = categorize_rsi(rsi)

        test = WaterTest(ph=ph, chlorine=chlorine, alkalinity=alkalinity,
                         hardness=hardness, temperature_c=temperature)
        dosing = recommend_dosing(test, config)

        dosing_data = [{"product": d.product, "amount": d.amount, "unit": d.unit, "reason": d.reason} for d in dosing]

        save_reading(session, ph=ph, chlorine=chlorine, alkalinity=alkalinity,
                     hardness=hardness, temperature_c=temperature,
                     lsi=lsi, rsi=rsi, dosing=dosing_data, notes=notes)
        st.session_state["last_result"] = {
            "ph": ph, "chlorine": chlorine, "alkalinity": alkalinity,
            "hardness": hardness, "temperature": temperature,
            "lsi": lsi, "lsi_cat": lsi_cat, "rsi": rsi, "rsi_cat": rsi_cat,
            "dosing": dosing,
        }
        st.rerun()

if "last_result" in st.session_state:
    r = st.session_state["last_result"]
    st.divider()

    col1, col2, col3 = st.columns(3)
    with col1:
        color = "green" if r["lsi_cat"] == "ausgeglichen" else ("red" if r["lsi_cat"] == "korrosiv" else "orange")
        st.markdown(f"### <span style='color:{color}'>LSI: {r['lsi']:+.2f}</span>", unsafe_allow_html=True)
        st.caption(f"→ {r['lsi_cat']}")
    with col2:
        st.markdown(f"### RSI: {r['rsi']:.1f}")
        st.caption(f"→ {r['rsi_cat']}")
    with col3:
        if r["dosing"]:
            st.warning("⚡ Handlungsbedarf!")
        else:
            st.success("✅ Wasser ist im Gleichgewicht")

    fig = go.Figure()
    fig.add_trace(go.Indicator(
        mode="gauge+number",
        value=r["lsi"],
        title={"text": "LSI"},
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
    st.plotly_chart(fig, use_container_width=True)

    if r["dosing"]:
        st.subheader("📋 Dosierempfehlung")
        for d in r["dosing"]:
            st.info(f"**{d.product}**: {d.amount:g} {d.unit}")
            st.caption(d.reason)

    st.page_link("app.py", label="← Zurück zum Dashboard", use_container_width=True)
