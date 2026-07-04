import streamlit as st


def render_sidebar(pools):
    pool_options = {}
    if len(pools) > 1:
        pool_options[0] = "Alle Pools"
    for p in pools:
        pool_options[p.id] = f"{p.name} ({p.volume_liter} L)"

    with st.sidebar:
        st.header("🏊 Pool")
        st.selectbox(
            "Pool auswählen",
            options=list(pool_options.keys()),
            format_func=lambda x: pool_options[x],
            key="pool_selector",
            label_visibility="collapsed",
        )

