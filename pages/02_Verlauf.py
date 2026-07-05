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

all_param_names = sorted(set(
    k for r in readings for k in getattr(r, '_values', {}).keys()
))

df = pd.DataFrame(
    [
        {
            "Datum": r.timestamp,
            **{n: r._values.get(n) for n in all_param_names},
            "Temperatur": r.temperature_c,
            "LSI": r.lsi_value,
            "RSI": r.rsi_value,
            "CSI": r.csi_value if r.csi_value is not None else None,
            "CCPP": r.ccpp_value if r.ccpp_value is not None else None,
        }
        for r in readings
    ]
)

param_names = [n for n in all_param_names if n not in ("lsi_value", "rsi_value", "csi_value")]
n_param_rows = len(param_names)
n_index_rows = 1
n_rows = n_param_rows + n_index_rows

subplot_titles = param_names + ["Indexwerte (LSI, RSI, CSI)"]
row_heights = [1.0 / n_rows] * n_rows

fig = make_subplots(rows=n_rows, cols=1, subplot_titles=subplot_titles, row_heights=row_heights)

for row_idx, name in enumerate(param_names, 1):
    if name in df.columns:
        fig.add_trace(
            go.Scatter(x=df["Datum"], y=df[name], name=name, mode="lines+markers"),
            row=row_idx, col=1,
        )

index_row = n_rows
for idx_name in ["LSI", "RSI"]:
    if idx_name in df.columns and df[idx_name].notna().any():
        fig.add_trace(
            go.Scatter(x=df["Datum"], y=df[idx_name], name=idx_name, mode="lines+markers"),
            row=index_row, col=1,
        )
if "CSI" in df.columns and df["CSI"].notna().any():
    fig.add_trace(
        go.Scatter(x=df["Datum"], y=df["CSI"], name="CSI", mode="lines+markers",
                   line=dict(dash="dot", width=3)),
        row=index_row, col=1,
    )

fig.update_layout(height=800, hovermode="x unified")
st.plotly_chart(fig, use_container_width=True)

st.subheader("📋 Alle Messwerte")
display_df = df.sort_values("Datum", ascending=False)
st.dataframe(display_df, use_container_width=True)

csv = display_df.to_csv(index=False, decimal=",", sep=";")
st.download_button(
    "📥 Als CSV exportieren", data=csv, file_name="messwerte.csv", mime="text/csv"
)
