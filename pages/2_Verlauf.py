import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from database.db import get_engine, init_db, get_session
from database.repository import get_readings_since

st.set_page_config(page_title="Verlauf", page_icon="📈")

engine = get_engine()
init_db(engine)
session = get_session(engine)

st.title("📈 Verlauf & Trends")

days = st.segmented_control("Zeitraum", ["7", "14", "30", "90"], default="30")
readings = get_readings_since(session, days=int(days))

if not readings:
    st.info("Noch keine Messwerte vorhanden.")
    st.stop()

df = pd.DataFrame([{
    "Datum": r.timestamp,
    "pH": r.ph,
    "Chlor": r.chlorine,
    "LSI": r.lsi_value,
    "RSI": r.rsi_value,
} for r in readings])

fig = make_subplots(rows=2, cols=1, subplot_titles=["pH & Chlor", "LSI & RSI"])
fig.add_trace(go.Scatter(x=df["Datum"], y=df["pH"], name="pH", mode="lines+markers"), row=1, col=1)
fig.add_trace(go.Scatter(x=df["Datum"], y=df["Chlor"], name="Chlor", mode="lines+markers"), row=1, col=1)
fig.add_trace(go.Scatter(x=df["Datum"], y=df["LSI"], name="LSI", mode="lines+markers"), row=2, col=1)
fig.add_trace(go.Scatter(x=df["Datum"], y=df["RSI"], name="RSI", mode="lines+markers"), row=2, col=1)

fig.update_layout(height=600, hovermode="x unified")
st.plotly_chart(fig, use_container_width=True)

st.subheader("📋 Alle Messwerte")
st.dataframe(df.sort_values("Datum", ascending=False), use_container_width=True)

csv = df.to_csv(index=False, decimal=",", sep=";")
st.download_button("📥 Als CSV exportieren", data=csv, file_name="messwerte.csv", mime="text/csv")

st.page_link("app.py", label="← Zurück zum Dashboard", use_container_width=True)
