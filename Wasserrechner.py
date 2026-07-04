import datetime
import os
import io
import streamlit as st
import plotly.graph_objects as go
from PIL import Image

from database.db import get_engine, init_db, get_session
from database.repository import (
    get_pools,
    get_pool,
    get_instruments,
    get_instrument,
    get_products,
    save_reading_for_pool,
    save_task,
    save_photo,
)
from pool_calculations.lsi import calculate_lsi, categorize_lsi
from pool_calculations.rsi import calculate_rsi, categorize_rsi
from pool_calculations.csi import calculate_csi, categorize_csi, calculate_ccpp
from pool_calculations.dosing import recommend_dosing_from_db
from pool_calculations.models import WaterTest
from utils.theme import inject_theme
from utils.nav import render_sidebar
from utils.task_dialog import task_dialog


def _target_gauge(value, title, axis_range, green_zone, unit=""):
    """Create a Plotly gauge with green zone = target range."""
    fig = go.Figure()
    green_min, green_max = green_zone
    steps = [
        {"range": [axis_range[0], green_min], "color": "red"},
        {"range": [green_min, green_max], "color": "mediumseagreen"},
        {"range": [green_max, axis_range[1]], "color": "red"},
    ]
    fig.add_trace(go.Indicator(
        mode="gauge+number",
        value=value,
        title={"text": f"{title} ({unit})" if unit else title},
        gauge={
            "axis": {"range": axis_range},
            "bar": {"color": "darkblue"},
            "steps": steps,
        },
    ))
    fig.update_layout(height=230, margin=dict(l=20, r=20, t=60, b=20))
    return fig


def _cat_score(cat: str) -> float:
    if cat in ("stark korrosiv",):
        return -1.5
    if cat in ("korrosiv",):
        return -1.0
    if cat == "ausgeglichen":
        return 0.0
    if cat in ("kalkend", "kalkausfällend"):
        return 0.5
    if cat in ("stark kalkend",):
        return 1.5
    return 0.0


def _cat_arrow_color(cat: str):
    if cat == "ausgeglichen":
        return "\u2705", "green"
    if "korrosiv" in cat:
        return "\U0001f534", "red"
    return "\U0001f7e0", "orange"


def _driver_analysis(ph, hardness, alkalinity, csi_cat, pool):
    issues = []
    if csi_cat in ("stark korrosiv", "korrosiv"):
        if pool.ph_min <= ph <= pool.ph_max:
            issues.append(("Calciumhärte oder Alkalinität erhöhen", "härtet/alk"))
        else:
            issues.append(("pH in Zielbereich bringen", "ph"))
    elif csi_cat in ("stark kalkend", "kalkend"):
        if ph > pool.ph_max:
            issues.append(("pH senken", "ph"))
        elif alkalinity > pool.alkalinity_max:
            issues.append(("Alkalinität senken", "alk"))
        elif hardness > pool.hardness_max:
            issues.append(("Calciumhärte senken (Teilwasserwechsel)", "härte"))
        else:
            issues.append(("pH oder Alkalinität prüfen", "allg"))
    return issues[0] if issues else ("", "")


st.set_page_config(
    page_title="PoolPilot - Dein intelligenter Pool-Helfer",
    page_icon="\U0001f3ca",
    layout="centered",
)

inject_theme()

st.markdown("""
<style>
button[data-baseweb="tab"] {
    font-size: 1.2rem !important;
    font-weight: 700 !important;
}
</style>
""", unsafe_allow_html=True)


engine = get_engine()
init_db(engine)
session = get_session(engine)

pools = get_pools(session)
if not pools:
    st.warning(
        "Kein Pool konfiguriert. Bitte lege unter 'Pools & Produkte' einen Pool an."
    )
    st.page_link("pages/01_Poolverwaltung.py", label="→ Pools & Produkte")
    st.stop()

selected_pool_id = st.session_state.get("pool_selector")
if selected_pool_id is None or selected_pool_id == 0:
    selected_pool_id = pools[0].id
pool = get_pool(session, selected_pool_id)

products = get_products(session)

tw_defaults = {"alkalinity": 100, "hardness": 200}
if pool.trinkwasser_id:
    from database.repository import get_trinkwasser

    tw = get_trinkwasser(session, pool.trinkwasser_id)
    if tw:
        tw_defaults = {
            "alkalinity": tw.alkalinity_default,
            "hardness": tw.calcium_hardness_default,
        }

st.title("\U0001f3ca PoolPilot")
st.caption(f"{pool.name} · {pool.volume_liter} Liter · {pool.pool_type} — Weil planschen im grünen Wasser keinen Spaß macht")

st.divider()

if "last_dosing" not in st.session_state:
    st.session_state.last_dosing = []
if "task_created" not in st.session_state:
    st.session_state.task_created = False
if "show_results" not in st.session_state:
    st.session_state.show_results = False

col_title, col_inst = st.columns([1, 1])
with col_title:
    st.markdown("### 1\uFE0F\u20E3 Messwerte erfassen")

help_texts = {
    "ph": "pH-Wert (Teststreifen 6,8–8,2). Ziel: 7,2–7,6. Beeinflusst Chlorwirkung und Wasserbalance.",
    "chlorine": "Freies Chlor in mg/L (Teststreifen 0,0–5,0). Ziel: 0,5–3,0 mg/L.",
    "temp": "Wassertemperatur in °C (separate Messung, z. B. Thermometer). Beeinflusst CSI/LSI/RSI direkt.",
    "alk": "Gesamtalkalinität (Teststreifen 0–240 mg/L CaCO₃). Pufferkapazität gegen pH-Schwankungen. Trinkwasser-Default: {} mg/L".format(tw_defaults["alkalinity"]),
    "hard": "Gesamthärte (Teststreifen 0–1000 mg/L CaCO₃). Wird als Calciumhärte für CSI/LSI genutzt. Trinkwasser-Default: {} mg/L".format(tw_defaults["hardness"]),
    "cya": "Cyanursäure / Stabilisator (Teststreifen 0–150 mg/L). Schützt Chlor vor UV-Abbau. Verfälscht Alkalinitätsmessung.",
    "salt": "Salzgehalt / TDS (Teststreifen 0–8000 mg/L NaCl). Relevant für CSI-Berechnung. Salzpool: ~3000–4000 mg/L.",
}

default_tds = 3000 if pool.pool_type == "salt" else 500

with col_inst:
    all_instruments = get_instruments(session)
    inst_options = {0: "Alle Parameter"} | {i.id: i.name for i in all_instruments}
    default_inst_index = 0
    if pool.instrument_id and pool.instrument_id in inst_options:
        default_inst_index = list(inst_options.keys()).index(pool.instrument_id)

    selected_inst_id = st.selectbox(
        "Messinstrument",
        options=list(inst_options.keys()),
        format_func=lambda x: inst_options[x],
        index=default_inst_index,
        key="measurement_instrument",
        label_visibility="collapsed",
    )

instrument = get_instrument(session, selected_inst_id) if selected_inst_id else None
instrument_name = instrument.name if instrument else "Teststreifen (alle Parameter)"

cap = {
    "ph": True,
    "chlorine": True,
    "alkalinity": True,
    "hardness": True,
    "cya": True,
    "salt": True,
}
if instrument:
    cap = {
        "ph": instrument.can_measure_ph,
        "chlorine": instrument.can_measure_chlorine or instrument.can_measure_bromine,
        "alkalinity": instrument.can_measure_alkalinity,
        "hardness": instrument.can_measure_hardness,
        "cya": instrument.can_measure_cya,
        "salt": instrument.can_measure_salt,
    }

def_val = {
    "ph": 7.4,
    "chlorine": 1.5,
    "alkalinity": tw_defaults["alkalinity"],
    "hardness": tw_defaults["hardness"],
    "cya": 0,
    "salt": default_tds,
}

st.markdown(f"#### \U0001f9ea {instrument_name}")
col1, col2 = st.columns(2)
with col1:
    if cap["ph"]:
        ph = st.slider("pH-Wert", 6.8, 8.2, 7.4, 0.1, help=help_texts["ph"])
    else:
        ph = def_val["ph"]
        st.metric("pH-Wert (aus Trinkwasser)", f"{ph:.1f}")

    if cap["chlorine"]:
        chlorine = st.slider("Freies Chlor (mg/L)", 0.0, 5.0, 1.5, 0.1, help=help_texts["chlorine"])
    else:
        chlorine = def_val["chlorine"]
        st.metric("Freies Chlor (aus Trinkwasser)", f"{chlorine:.1f} mg/L")

    if cap["alkalinity"]:
        alkalinity = st.slider("Gesamtalkalinität (mg/L CaCO₃)", 0, 240, int(def_val["alkalinity"]), 5, help=help_texts["alk"])
    else:
        alkalinity = int(def_val["alkalinity"])
        st.metric("Gesamtalkalinität (aus Trinkwasser)", f"{alkalinity} mg/L")
with col2:
    if cap["hardness"]:
        hardness = st.slider("Gesamthärte (mg/L CaCO₃)", 0, 1000, int(def_val["hardness"]), 10, help=help_texts["hard"])
    else:
        hardness = int(def_val["hardness"])
        st.metric("Gesamthärte (aus Trinkwasser)", f"{hardness} mg/L")

    if cap["cya"]:
        cya = st.slider("Cyanursäure / CYA (mg/L)", 0, 150, 0, 5, help=help_texts["cya"])
    else:
        cya = 0
        st.metric("Cyanursäure / CYA (aus Trinkwasser)", f"{cya} mg/L")

    if cap["salt"]:
        tds = st.slider("Salzgehalt / TDS (mg/L NaCl)", 0, 8000, default_tds, 100, help=help_texts["salt"])
    else:
        tds = default_tds
        st.metric("Salzgehalt / TDS (aus Trinkwasser)", f"{tds} mg/L NaCl")

st.markdown("#### \U0001f321\uFE0F Separate Messung")
col_temp, col_water = st.columns(2)
with col_temp:
    temperature = st.slider(
        "Wassertemperatur (°C)",
        0, 45, int(pool.temperature_default), 1,
        key="temp_horizontal",
    )
with col_water:
    if pool.max_fill_height_cm and pool.min_fill_height_cm and pool.max_fill_height_cm > pool.min_fill_height_cm:
        lo = 0
        hi = int(pool.max_fill_height_cm * 1.5)
        min_cm = pool.min_fill_height_cm
        max_cm = pool.max_fill_height_cm
        water_level_cm = st.slider(
            "Wasserstand (cm)",
            lo, hi,
            int(pool.min_fill_height_cm),
            1,
            format="%d cm",
        )

        pct = lambda v: v / hi * 100
        st.markdown(f"""
<div style="display:flex;align-items:center;gap:4px;margin:-14px 0 16px;font-size:11px;color:#555">
<span>\u25b2 {hi}</span>
<div style="flex:1;height:8px;background:linear-gradient(to right,#e0e0e0 {pct(min_cm)}%,#81c784 {pct(min_cm)}%,#81c784 {pct(max_cm)}%,#e0e0e0 {pct(max_cm)}%);border-radius:4px;position:relative">
    <div style="position:absolute;left:{pct(water_level_cm)}%;top:-2px;width:2px;height:12px;background:#333;border-radius:1px"></div>
</div>
<span>\u25bc 0</span>
</div>
""", unsafe_allow_html=True)
        pool_shape = pool.shape or "rechteckig"
        if pool_shape == "rechteckig" and pool.inner_length_cm and pool.inner_width_cm:
            cur_area = pool.inner_length_cm * pool.inner_width_cm
        elif pool_shape == "rund" and pool.inner_diameter_cm:
            cur_area = 3.14159 * (pool.inner_diameter_cm / 2) ** 2
        else:
            cur_area = None
        if cur_area:
            cur_vol = cur_area * water_level_cm / 1000
            st.caption(f"Volumen: **{cur_vol:,.0f} L**")
    else:
        st.info("Wasserstand: Min/Max in Pool-Einstellungen hinterlegen.")

notes = st.text_input(
    "\U0001f4dd Notizen (optional)", placeholder="z. B. Wetter, Wasserstand..."
)

st.markdown("#### \U0001f4f8 Foto")
photo_source = st.radio(
    "Foto-Quelle",
    ["\U0001f4c1 Hochladen", "\U0001f4f8 Kamera"],
    horizontal=True,
    label_visibility="collapsed",
)
uploaded_file = None
camera_file = None
if photo_source == "\U0001f4f8 Kamera":
    camera_file = st.camera_input("\U0001f4f8 Mit Kamera aufnehmen")
else:
    uploaded_file = st.file_uploader(
        "\U0001f4c1 Vom Gerät hochladen", type=["jpg", "jpeg", "png"]
    )

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

lsi = calculate_lsi(ph, temperature, hardness, alkalinity, cya=cya, tds=tds)
rsi = calculate_rsi(ph, temperature, hardness, alkalinity)
csi = calculate_csi(ph, temperature, hardness, alkalinity, cya=cya, tds=tds)
ccpp = calculate_ccpp(ph, temperature, hardness, alkalinity, cya=cya, tds=tds)
lsi_cat = categorize_lsi(lsi)
rsi_cat = categorize_rsi(rsi)
csi_cat = categorize_csi(csi)

test = WaterTest(
    ph=ph,
    chlorine=chlorine,
    alkalinity=alkalinity,
    hardness=hardness,
    temperature_c=temperature,
)
dosing = recommend_dosing_from_db(test, pool, products)

if st.button("\U0001f4be Messung speichern", type="primary", use_container_width=True):
    dosing_data = (
        [
            {
                "product": d.product,
                "amount": d.amount,
                "unit": d.unit,
                "reason": d.reason,
            }
            for d in dosing
        ]
        if dosing
        else []
    )

    reading = save_reading_for_pool(
        session,
        pool_id=selected_pool_id,
        ph=ph,
        chlorine=chlorine,
        alkalinity=alkalinity,
        hardness=hardness,
        temperature_c=temperature,
        lsi=lsi,
        rsi=rsi,
        csi=csi,
        ccpp=ccpp,
        dosing=dosing_data,
        notes=notes,
    )

    if photo_path:
        save_photo(
            session,
            image_path=photo_path,
            caption=f"Messung {datetime.datetime.now().strftime('%d.%m.%Y %H:%M')}",
        )

    if not st.session_state.get("task_created"):
        for d in dosing:
            save_task(
                session,
                task_type="dosierung",
                title=f"{d.product}: {d.amount:g} {d.unit}",
                description=d.reason,
                due_date=datetime.date.today(),
                interval_days=0,
                product_id=getattr(d, 'product_id', None),
                product_name=d.product,
                recommended_amount=d.amount,
                recommended_unit=d.unit,
            )

    st.success("\u2705 Messung gespeichert!")
    st.session_state.show_results = True
    st.session_state.last_dosing = dosing
    st.session_state.task_created = False
    pool_id = st.session_state.get("selected_pool_id")
    if pool_id:
        pool = get_pool(session, pool_id)
        if pool and pool.auto_measurement_task_days > 0:
            follow_up_date = datetime.date.today() + datetime.timedelta(days=pool.auto_measurement_task_days)
            save_task(
                session,
                task_type="nachkontrolle",
                title="Nachkontrolle (Messung)",
                description=f"Automatisch erstellt nach Messung vom {datetime.date.today().isoformat()}",
                due_date=follow_up_date,
                interval_days=pool.auto_measurement_task_days,
                pool_id=pool_id,
            )
    if "executed_actions" in st.session_state:
        del st.session_state.executed_actions

if st.session_state.last_dosing:
    with st.expander("Letzte gespeicherte Messung"):
        st.json(
            [
                {
                    "product": d.product,
                    "amount": d.amount,
                    "unit": d.unit,
                    "reason": d.reason,
                }
                for d in st.session_state.last_dosing
            ]
        )

st.divider()

if st.session_state.show_results:
    st.subheader("2\uFE0F\u20E3 Schlussfolgerungen")
    tab_dosis, tab_hygiene, tab_kalk = st.tabs(["\U0001f48a Dosierempfehlung", "\U0001f9fc Hygiene", "\u2696\uFE0F Kalk-Korrosion"])

    with tab_dosis:
        ph_ok = pool.ph_min <= ph <= pool.ph_max
        chl_ok = pool.chlorine_min <= chlorine <= pool.chlorine_max
        alk_ok = pool.alkalinity_min <= alkalinity <= pool.alkalinity_max
        hard_ok = pool.hardness_min <= hardness <= pool.hardness_max
        consensus_score = 0.6 * _cat_score(csi_cat) + 0.2 * _cat_score(lsi_cat) + 0.2 * _cat_score(rsi_cat)
        has_kalk_issue = consensus_score < -0.3 or consensus_score > 0.3
        all_ok = ph_ok and chl_ok and alk_ok and hard_ok and not has_kalk_issue

        if "done_list" not in st.session_state:
            st.session_state.done_list = set()

        if all_ok:
            st.success("\u2705 Alles im grünen Bereich — keine Maßnahmen nötig.")
        else:
            issue_count = sum([not ph_ok, not chl_ok, not alk_ok, not hard_ok, has_kalk_issue])
            worst = "kritisch" if consensus_score < -0.5 or consensus_score > 0.5 else "erhöht"
            st.warning(f"\u26a1 **{issue_count} Handlungsfeld{'er' if issue_count > 1 else ''}** — Zustand {worst}")

            order_steps = []
            if not alk_ok:
                order_steps.append("1\uFE0F\u20E3 Alkalinität (Puffer für pH)")
            if not ph_ok:
                order_steps.append("2\uFE0F\u20E3 pH-Wert")
            if not hard_ok:
                order_steps.append("3\uFE0F\u20E3 Calciumhärte")
            if has_kalk_issue:
                direction = "korrosiv \U0001f534" if consensus_score < -0.3 else "kalkend \U0001f7e0"
                order_steps.append(f"4\uFE0F\u20E3 Kalk-Korrosion ({direction})")
            if not chl_ok:
                order_steps.append("5\uFE0F\u20E3 Chlor (Desinfektion)")
            st.caption(" | ".join(order_steps) if order_steps else "")

            for d in dosing:
                done_key = f"done_{d.product}"
                is_done = done_key in st.session_state.done_list

                with st.container(border=True):
                    cols = st.columns([2, 1, 1])
                    with cols[0]:
                        badge = {1: "\U0001f534", 2: "\U0001f7e0", 3: "\U0001f7e1", 4: "\U0001f535", 5: "\u26aa"}.get(d.priority, "\u26aa")
                        st.markdown(f"**{badge} {d.product}**")
                        st.markdown(f"### {d.amount:g} {d.unit}")
                        st.caption(d.reason)
                        if d.instruction:
                            st.markdown(f"\U0001f4d6 *{d.instruction}*")
                        if d.wait_minutes > 0:
                            st.caption(f"\u23f1 Nach Zugabe ~{d.wait_minutes} Min. warten, dann neu testen")
                    with cols[1]:
                        st.markdown(f"<br>", unsafe_allow_html=True)
                        if st.button(
                            "\U0001f4cb Aufgabe", key=f"task_{d.product}",
                            use_container_width=True,
                        ):
                            task = save_task(
                                session,
                                task_type="dosierung",
                                title=f"{d.product}: {d.amount:g} {d.unit}",
                                description=d.reason,
                                due_date=datetime.date.today(),
                                interval_days=0,
                            )
                            st.session_state.cal_selected_task_id = task.id
                            st.session_state.cal_click_seed = st.session_state.get("cal_click_seed", 0) + 1
                            st.rerun()
                    with cols[2]:
                        if is_done:
                            st.success("\u2705 Erledigt")
                        else:
                            st.markdown(f"<br>", unsafe_allow_html=True)
                            if st.button(
                                "\u2705 Erledigt", key=f"done_{d.product}",
                                use_container_width=True, type="primary",
                            ):
                                task_data = {
                                    "date": datetime.date.today().isoformat(),
                                    "time": datetime.datetime.now().strftime("%H:%M"),
                                    "product": d.product,
                                    "amount": d.amount,
                                    "unit": d.unit,
                                    "reason": d.reason,
                                }
                                if "executed_actions" not in st.session_state:
                                    st.session_state.executed_actions = []
                                st.session_state.executed_actions.append(task_data)
                                st.session_state.done_list.add(done_key)
                                if d.follow_up_days > 0:
                                    save_task(
                                        session,
                                        task_type="nachkontrolle",
                                        title=f"{d.product} – Nachkontrolle",
                                        description=(
                                            f"Folgeaufgabe in {d.follow_up_days} Tagen "
                                            f"(auto. {datetime.date.today().isoformat()})"
                                        ),
                                        due_date=datetime.date.today()
                                        + datetime.timedelta(days=d.follow_up_days),
                                        interval_days=d.follow_up_days,
                                        product_id=getattr(d, 'product_id', None),
                                        product_name=d.product,
                                        recommended_amount=d.amount,
                                        recommended_unit=d.unit,
                                    )
                                st.rerun()

                    if is_done:
                        with st.expander("\U0001f4dd Details zur Ausführung", expanded=False):
                            st.text_input(
                                "Was genau wurde gemacht?",
                                placeholder=f"z. B. {d.amount:g} {d.unit} in Wasser gelöst und zugegeben",
                                key=f"exec_note_{d.product}",
                            )

        all_done = all(
            f"done_{d.product}" in st.session_state.done_list
            for d in dosing
        ) if dosing else True

        if dosing and all_done and not all_ok:
            st.success("\U0001f3af Alle Maßnahmen als erledigt markiert! Nach Einwirkzeit neu testen.")

    with tab_hygiene:
        col_ph_gauge, col_chlor_gauge = st.columns(2)
        with col_ph_gauge:
            ph_fig = _target_gauge(ph, "pH", [6.2, 8.4], [pool.ph_min, pool.ph_max])
            st.plotly_chart(ph_fig, use_container_width=True)
            ph_ok = pool.ph_min <= ph <= pool.ph_max
            st.metric("pH", f"{ph:.1f}", delta="\u2705 i.O." if ph_ok else f"\u26a0\uFE0F Ziel {pool.ph_min}–{pool.ph_max}")
        with col_chlor_gauge:
            chl_fig = _target_gauge(chlorine, "Chlor", [0.0, 10.0], [pool.chlorine_min, pool.chlorine_max], unit="mg/L")
            st.plotly_chart(chl_fig, use_container_width=True)
            chl_ok = pool.chlorine_min <= chlorine <= pool.chlorine_max
            st.metric("Chlor", f"{chlorine:.1f} mg/L", delta="\u2705 i.O." if chl_ok else f"\u26a0\uFE0F Ziel {pool.chlorine_min}–{pool.chlorine_max} mg/L")

    with tab_kalk:
        csi_score = _cat_score(csi_cat)
        lsi_score = _cat_score(lsi_cat)
        rsi_score = _cat_score(rsi_cat)
        consensus = 0.6 * csi_score + 0.2 * lsi_score + 0.2 * rsi_score

        if consensus < -0.3:
            cons_verdict = "korrosiv"
            cons_msg = "\U0001f534 Wasser tendiert zu korrosiv — Oberflächen- und Metallschäden möglich"
            cons_what = "Calciumhärte oder Alkalinität erhöhen, pH anheben"
        elif consensus > 0.3:
            cons_verdict = "kalkend"
            cons_msg = "\U0001f7e0 Wasser tendiert zu kalkend — Beläge und Trübungen möglich"
            cons_what = "pH oder Alkalinität senken"
        else:
            cons_verdict = "ausgeglichen"
            cons_msg = "\u2705 Wasser im Kalk-Korrosion Gleichgewicht"
            cons_what = ""

        col_csi, col_lsi, col_rsi = st.columns(3)
        with col_csi:
            csi_arr, csi_col = _cat_arrow_color(csi_cat)
            st.markdown(f"### {csi_arr} CSI: <span style='color:{csi_col}'>{csi:+.2f}</span>", unsafe_allow_html=True)
            if ccpp > 0:
                st.caption(f"\u2b07\uFE0F Kalkfall: ~{ccpp} mg/L CaCO₃ möglich")
        with col_lsi:
            lsi_arr, lsi_col = _cat_arrow_color(lsi_cat)
            st.markdown(f"### {lsi_arr} LSI: <span style='color:{lsi_col}'>{lsi:+.2f}</span>", unsafe_allow_html=True)
        with col_rsi:
            rsi_arr, rsi_col = _cat_arrow_color(rsi_cat)
            st.markdown(f"### {rsi_arr} RSI: <span style='color:{rsi_col}'>{rsi:.1f}</span>", unsafe_allow_html=True)

        if cons_verdict == "ausgeglichen":
            st.success(cons_msg)
        else:
            st.warning(cons_msg)
            if cons_what:
                st.caption(f"→ {cons_what}")

        cats = [csi_cat, lsi_cat, rsi_cat]
        unique = set(c.replace("stark ", "").replace("kalkausfällend", "kalkend") for c in cats)
        if len(unique) > 1:
            notes = []
            if "ausgeglichen" not in unique:
                notes.append("Kein Index zeigt ausgeglichenes Wasser")
            if csi_cat != lsi_cat.replace("kalkausfällend", "kalkend"):
                if cya > 0 or tds > 500:
                    notes.append("CSI korrigiert LSI um CYA/TDS-Effekte")
            if rsi_cat == "ausgeglichen" and cons_verdict != "ausgeglichen":
                notes.append("RSI toleranter — optimiert für Metallschutz")
            if notes:
                st.info("\U0001f4a1 " + " | ".join(notes))

        gauge_csi, gauge_lsi, gauge_rsi = st.columns(3)
        with gauge_csi:
            csi_fig = go.Figure()
            csi_fig.add_trace(go.Indicator(
                mode="gauge+number", value=csi, title={"text": "CSI (Wojtowicz)"},
                gauge={"axis": {"range": [-2, 2]}, "bar": {"color": "darkblue"},
                       "steps": [
                           {"range": [-2, -0.5], "color": "red"},
                           {"range": [-0.5, -0.3], "color": "orangered"},
                           {"range": [-0.3, 0.3], "color": "green"},
                           {"range": [0.3, 0.5], "color": "orange"},
                           {"range": [0.5, 2], "color": "darkorange"},
                       ]},
            ))
            csi_fig.update_layout(height=230, margin=dict(l=20, r=20, t=60, b=20))
            st.plotly_chart(csi_fig, use_container_width=True)
        with gauge_lsi:
            lsi_fig = go.Figure()
            lsi_fig.add_trace(go.Indicator(
                mode="gauge+number", value=lsi, title={"text": "LSI"},
                gauge={"axis": {"range": [-2, 2]}, "bar": {"color": "darkblue"},
                       "steps": [
                           {"range": [-2, -0.5], "color": "red"},
                           {"range": [-0.5, 0.5], "color": "green"},
                           {"range": [0.5, 2], "color": "orange"},
                       ]},
            ))
            lsi_fig.update_layout(height=230, margin=dict(l=20, r=20, t=60, b=20))
            st.plotly_chart(lsi_fig, use_container_width=True)
        with gauge_rsi:
            rsi_fig = go.Figure()
            rsi_fig.add_trace(go.Indicator(
                mode="gauge+number", value=rsi, title={"text": "RSI"},
                gauge={"axis": {"range": [3, 11]}, "bar": {"color": "darkblue"},
                       "steps": [
                           {"range": [3, 5], "color": "orange"},
                           {"range": [5, 7], "color": "green"},
                           {"range": [7, 11], "color": "red"},
                       ]},
            ))
            rsi_fig.update_layout(height=230, margin=dict(l=20, r=20, t=60, b=20))
            st.plotly_chart(rsi_fig, use_container_width=True)

        with st.expander("\u2139\uFE0F Detailwissen: CSI, LSI, RSI & Hamilton Index"):
            st.markdown(f"""
        **CSI (Calcium Sättigungs-Index)** – Wojtowicz 2001 (Modernster Standard)
        Bereich: **-0,3 bis +0,3** (ausgeglichen).
        Korrigiert die Alkalinität um Cyanursäure (CYA) {f'({cya} mg/L)' if cya > 0 else ''}
        und berücksichtigt TDS/Salzgehalt {f'({tds} mg/L)' if tds > 500 else ''}.
        *CSI ist der primäre Index für die Wasserbalance (Gewichtung 60%).*

        **LSI (Langelier Sättigungs-Index)** – PHTA-Klassiker
        Bereich: -0,5 bis +0,5 (ausgeglichen). Vereinfachte Formel ohne CYA-Korrektur.
        *Referenz für die Wasserbalance (Gewichtung 20%).*

        **RSI (Ryznar Stabilitäts-Index)** – Empirisch, Fokus Metalle
        Bereich: **5,0–7,0** (ausgeglichen, PHTA-Standard).
        Optimiert für Korrosionsschutz von Heizern/Rohren (Gewichtung 20%).

        **Hamilton Index** – Praxistabelle von Jock Hamilton (1960er)
        Empfiehlt pH 7,8–8,2. Nutzt Gesamthärte vs. Gesamtalkalinität.
        Ignoriert Temperatur, TDS, Cyanursäure.

        **CCPP (Calcium Carbonate Precipitation Potential)** – Nur bei CSI > +0,3
        Gibt an, wie viel mg/L CaCO₃ ausfallen könnten. Richtwert: < 10 mg/L = gering.
            """)



render_sidebar(pools)

if st.session_state.get("cal_selected_task_id"):
    task_dialog(st.session_state.cal_selected_task_id, session, pools, products)
