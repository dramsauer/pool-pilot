import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from database.db import get_engine, init_db, get_session
from database.repository import get_pools, get_readings_since, get_readings_for_pool
from utils.theme import inject_theme
from utils.nav import render_sidebar

st.set_page_config(
    page_title="PoolPilot - Dein intelligenter Pool-Helfer", page_icon="🏊"
)
inject_theme()

engine = get_engine()
init_db(engine)
session = get_session(engine)

pools = get_pools(session)
render_sidebar(pools)

st.title("📈 Verlauf & Trends")

selected_pool_id = st.session_state.get("pool_selector", 0)

days = st.segmented_control("Zeitraum", ["7", "14", "30", "90"], default="30")

if selected_pool_id and selected_pool_id != 0:
    readings = get_readings_for_pool(session, selected_pool_id, limit=200)
else:
    readings = get_readings_since(session, days=int(days))
    readings = [r for r in readings]

if not readings:
    st.info("Noch keine Messwerte vorhanden.")
    st.stop()

df = pd.DataFrame(
    [
        {
            "Datum": r.timestamp,
            "pH": r.ph,
            "Chlor": r.chlorine,
            "Alkalinität": r.alkalinity,
            "Härte": r.hardness,
            "LSI": r.lsi_value,
            "RSI": r.rsi_value,
            "CSI": r.csi_value if r.csi_value is not None else None,
            "CCPP": r.ccpp_value if r.ccpp_value is not None else None,
        }
        for r in readings
    ]
)

has_csi = df["CSI"].notna().any()
has_ccpp = df["CCPP"].notna().any()

if has_csi:
    fig = make_subplots(
        rows=3,
        cols=1,
        subplot_titles=[
            "pH & Chlor",
            "Alkalinität & Calciumhärte",
            "CSI, LSI & RSI",
        ],
        row_heights=[0.33, 0.33, 0.33],
    )
else:
    fig = make_subplots(
        rows=3,
        cols=1,
        subplot_titles=["pH & Chlor", "Alkalinität & Calciumhärte", "LSI & RSI"],
        row_heights=[0.33, 0.33, 0.33],
    )

fig.add_trace(
    go.Scatter(x=df["Datum"], y=df["pH"], name="pH", mode="lines+markers"), row=1, col=1
)
fig.add_trace(
    go.Scatter(x=df["Datum"], y=df["Chlor"], name="Chlor", mode="lines+markers"),
    row=1,
    col=1,
)
fig.add_trace(
    go.Scatter(
        x=df["Datum"], y=df["Alkalinität"], name="Alkalinität", mode="lines+markers"
    ),
    row=2,
    col=1,
)
fig.add_trace(
    go.Scatter(x=df["Datum"], y=df["Härte"], name="Härte", mode="lines+markers"),
    row=2,
    col=1,
)
fig.add_trace(
    go.Scatter(x=df["Datum"], y=df["LSI"], name="LSI", mode="lines+markers"),
    row=3,
    col=1,
)
fig.add_trace(
    go.Scatter(x=df["Datum"], y=df["RSI"], name="RSI", mode="lines+markers"),
    row=3,
    col=1,
)
if has_csi:
    fig.add_trace(
        go.Scatter(
            x=df["Datum"],
            y=df["CSI"],
            name="CSI",
            mode="lines+markers",
            line=dict(dash="dot", width=3),
        ),
        row=3,
        col=1,
    )

fig.update_layout(height=700, hovermode="x unified")
st.plotly_chart(fig, use_container_width=True)

st.subheader("📋 Alle Messwerte")
display_df = df.sort_values("Datum", ascending=False)
st.dataframe(display_df, use_container_width=True)

csv = display_df.to_csv(index=False, decimal=",", sep=";")
st.download_button(
    "📥 Als CSV exportieren", data=csv, file_name="messwerte.csv", mime="text/csv"
)
