import streamlit as st
from database.db import get_engine, init_db, get_session
from database.repository import (
    save_pool,
    get_pools,
    get_pool,
    update_pool,
    delete_pool,
    save_trinkwasser,
    get_trinkwasser_quellen,
    delete_trinkwasser,
    save_product,
    get_products,
    update_product,
    delete_product,
    get_instruments,
    get_instrument,
    save_instrument,
    update_instrument,
    delete_instrument,
    get_task_templates,
    get_pool_task_defaults,
    set_pool_template_active,
    activate_defaults_for_pool,
)

st.set_page_config(
    page_title="PoolPilot - Dein intelligenter Pool-Helfer", page_icon="🏊"
)

engine = get_engine()
init_db(engine)
session = get_session(engine)

st.title("🏊 Pools & Produkte")

tab1, tab2, tab3, tab4 = st.tabs(["Pools", "Trinkwasser-Quellen", "Produkte", "Messinstrumente"])

with tab1:
    st.subheader("Pool verwalten")
    pools = get_pools(session)
    if pools:
        pool_names = {p.id: p.name for p in pools}
        selected_id = st.selectbox(
            "Pool auswählen",
            options=list(pool_names.keys()),
            format_func=lambda x: pool_names[x],
        )
        pool = get_pool(session, selected_id)
    else:
        pool = None

    with st.form("pool_form"):
        name = st.text_input("Name", value=pool.name if pool else "")
        col1, col2 = st.columns(2)
        with col1:
            volume = st.number_input(
                "Volumen (L)",
                min_value=1,
                value=int(pool.volume_liter) if pool else 1000,
            )
        with col2:
            ptype = st.selectbox(
                "Typ",
                ["chlorine", "bromine"],
                index=0 if not pool or pool.pool_type == "chlorine" else 1,
            )
        col1, col2 = st.columns(2)
        with col1:
            ph_min = st.number_input(
                "pH min", 0.0, 14.0, value=pool.ph_min if pool else 7.2, step=0.1
            )
        with col2:
            ph_max = st.number_input(
                "pH max", 0.0, 14.0, value=pool.ph_max if pool else 7.6, step=0.1
            )
        col1, col2 = st.columns(2)
        with col1:
            chl_min = st.number_input(
                "Chlor min (mg/L)",
                0.0,
                10.0,
                value=pool.chlorine_min if pool else 0.5,
                step=0.1,
            )
        with col2:
            chl_max = st.number_input(
                "Chlor max (mg/L)",
                0.0,
                10.0,
                value=pool.chlorine_max if pool else 3.0,
                step=0.1,
            )
        col1, col2 = st.columns(2)
        with col1:
            alk_min = st.number_input(
                "Alkalinität min",
                0,
                500,
                value=int(pool.alkalinity_min if pool else 80),
            )
        with col2:
            alk_max = st.number_input(
                "Alkalinität max",
                0,
                500,
                value=int(pool.alkalinity_max if pool else 120),
            )
        col1, col2 = st.columns(2)
        with col1:
            hard_min = st.number_input(
                "Härte min", 0, 500, value=int(pool.hardness_min if pool else 150)
            )
        with col2:
            hard_max = st.number_input(
                "Härte max", 0, 500, value=int(pool.hardness_max if pool else 250)
            )
        temp_default = st.number_input(
            "Standard-Temperatur (°C)",
            0,
            45,
            value=int(pool.temperature_default if pool else 35),
        )

        st.markdown("##### 📐 Beckenmaße & Füllhöhen")
        st.caption("Maße eingeben → Volumen bei Min/Max wird automatisch berechnet.")
        dim_col1, dim_col2 = st.columns(2)
        with dim_col1:
            p_shape = st.selectbox(
                "Form", ["rechteckig", "rund"],
                index=0 if not pool or pool.shape in (None, "rechteckig") else 1,
            )
            if p_shape == "rechteckig":
                p_len = st.number_input(
                    "Innenlänge (cm)", min_value=1, value=int(pool.inner_length_cm or 132) if pool else 132,
                    key="pool_inner_len",
                )
                p_wid = st.number_input(
                    "Innenbreite (cm)", min_value=1, value=int(pool.inner_width_cm or 132) if pool else 132,
                    key="pool_inner_wid",
                )
                area = p_len * p_wid
            else:
                p_dia = st.number_input(
                    "Innendurchmesser (cm)", min_value=1, value=int(pool.inner_diameter_cm or 132) if pool else 132,
                    key="pool_inner_dia",
                )
                area = 3.14159 * (p_dia / 2) ** 2
            st.metric("Grundfläche (innen)", f"{area:,.0f} cm²")
        with dim_col2:
            p_fill_max = st.number_input(
                "Max-Markierung (cm)", min_value=0.0, value=pool.max_fill_height_cm if pool else 45.0, step=0.5,
                key="pool_fill_max", help="Wasserstand bei Max-Markierung (ab Boden)",
            )
            p_fill_min = st.number_input(
                "Min-Markierung (cm)", min_value=0.0, value=pool.min_fill_height_cm if pool else 35.0, step=0.5,
                key="pool_fill_min", help="Wasserstand bei Min-Markierung (ab Boden)",
            )
            v_at_max = area * p_fill_max / 1000
            v_at_min = area * p_fill_min / 1000
            st.metric("Volumen bei Max", f"{v_at_max:,.0f} L")
            st.metric("Volumen bei Min", f"{v_at_min:,.0f} L")
            volume = int(v_at_max)

        tw_quellen = get_trinkwasser_quellen(session)
        tw_options = {0: "Keine"} | {tw.id: tw.name for tw in tw_quellen}
        tw_id = st.selectbox(
            "Trinkwasser-Quelle",
            options=list(tw_options.keys()),
            format_func=lambda x: tw_options[x],
            index=list(tw_options.keys()).index(pool.trinkwasser_id)
            if pool and pool.trinkwasser_id in tw_options
            else 0,
        )

        instruments = get_instruments(session)
        inst_options = {0: "Keines"} | {i.id: i.name for i in instruments}
        inst_id = st.selectbox(
            "Messinstrument",
            options=list(inst_options.keys()),
            format_func=lambda x: inst_options[x],
            index=list(inst_options.keys()).index(pool.instrument_id)
            if pool and pool.instrument_id in inst_options
            else 0,
        )

        st.markdown("##### 📋 Standard-Aufgaben")
        st.caption("Wiederkehrende Aufgaben, die automatisch im Wartung-Kalender erscheinen.")
        templates = get_task_templates(session)
        pool_defaults = {ptd.template_id: ptd for ptd in get_pool_task_defaults(session, pool.id)} if pool else {}
        active_template_ids = set()
        for ptd in pool_defaults.values():
            if ptd.active:
                active_template_ids.add(ptd.template_id)

        cat_labels = {"chemie": "🧪 Chemie", "technik": "🔧 Technik", "reinigung": "🧹 Reinigung", "allgemein": "📋 Allgemein"}
        cats_order = ["chemie", "technik", "reinigung", "allgemein"]
        templates_by_cat: dict[str, list] = {}
        for t in templates:
            cat = t.category if t.category in cats_order else "allgemein"
            templates_by_cat.setdefault(cat, []).append(t)

        selected_templates = set()
        for cat in cats_order:
            if cat in templates_by_cat:
                st.markdown(f"**{cat_labels.get(cat, cat)}**")
                cols = st.columns(2)
                for i, t in enumerate(templates_by_cat[cat]):
                    with cols[i % 2]:
                        default_val = t.id in active_template_ids if pool else True
                        if st.checkbox(
                            f"{t.icon} {t.name} ({t.interval_days} Tage)",
                            value=default_val,
                            key=f"tmpl_{t.id}",
                        ):
                            selected_templates.add(t.id)

        auto_task_days = st.number_input(
            "Auto-Nachkontrolle nach Messung (Tage, 0=aus)",
            min_value=0, max_value=365,
            value=pool.auto_measurement_task_days if pool else 7,
            key="auto_task_days",
        )

        submitted = st.form_submit_button("Speichern")
        if submitted:
            dim_kwargs = {
                "shape": p_shape,
                "min_fill_height_cm": p_fill_min,
                "max_fill_height_cm": p_fill_max,
            }
            if p_shape == "rechteckig":
                dim_kwargs.update(inner_length_cm=p_len, inner_width_cm=p_wid, inner_diameter_cm=None)
            else:
                dim_kwargs.update(inner_diameter_cm=p_dia, inner_length_cm=None, inner_width_cm=None)

            if pool:
                update_pool(
                    session,
                    pool.id,
                    name=name,
                    volume_liter=volume,
                    pool_type=ptype,
                    ph_min=ph_min,
                    ph_max=ph_max,
                    chlorine_min=chl_min,
                    chlorine_max=chl_max,
                    alkalinity_min=alk_min,
                    alkalinity_max=alk_max,
                    hardness_min=hard_min,
                    hardness_max=hard_max,
                    temperature_default=temp_default,
                    trinkwasser_id=tw_id if tw_id else None,
                    instrument_id=inst_id if inst_id else None,
                    auto_measurement_task_days=auto_task_days,
                    **dim_kwargs,
                )
                st.success("Pool aktualisiert!")
                for t in templates:
                    is_active = t.id in selected_templates
                    set_pool_template_active(session, pool.id, t.id, is_active)
            else:
                new_pool = save_pool(
                    session,
                    name=name,
                    volume_liter=volume,
                    pool_type=ptype,
                    ph_min=ph_min,
                    ph_max=ph_max,
                    chlorine_min=chl_min,
                    chlorine_max=chl_max,
                    alkalinity_min=alk_min,
                    alkalinity_max=alk_max,
                    hardness_min=hard_min,
                    hardness_max=hard_max,
                    temperature_default=temp_default,
                    trinkwasser_id=tw_id if tw_id else None,
                    instrument_id=inst_id if inst_id else None,
                    auto_measurement_task_days=auto_task_days,
                    **dim_kwargs,
                )
                activate_defaults_for_pool(session, new_pool.id)
                for t in templates:
                    is_active = t.id in selected_templates
                    set_pool_template_active(session, new_pool.id, t.id, is_active)
                st.success("Pool angelegt!")

    st.divider()
    if pool:
        if st.button("Pool löschen", type="secondary"):
            delete_pool(session, pool.id)
            st.rerun()
    st.button("Neuen Pool anlegen", on_click=lambda: None)

with tab2:
    st.subheader("Trinkwasser-Quellen")
    for tw in get_trinkwasser_quellen(session):
        with st.expander(f"📡 {tw.name}"):
            st.write(f"pH: {tw.ph_default}")
            st.write(f"Alkalinität: {tw.alkalinity_default} mg/L")
            st.write(f"Calciumhärte: {tw.calcium_hardness_default} mg/L")
            if tw.notes:
                st.caption(tw.notes)
            if st.button("Löschen", key=f"del_tw_{tw.id}"):
                delete_trinkwasser(session, tw.id)
                st.rerun()

    st.divider()
    with st.form("new_trinkwasser"):
        st.subheader("Neue Quelle")
        tw_name = st.text_input("Name", value="Stamsried – Kreiswerke Cham")
        col1, col2, col3 = st.columns(3)
        with col1:
            tw_ph = st.number_input("pH", 0.0, 14.0, value=7.5, step=0.1)
        with col2:
            tw_alk = st.number_input("Alkalinität (mg/L)", 0, 500, value=145)
        with col3:
            tw_hard = st.number_input("Calciumhärte (mg/L)", 0, 500, value=185)
        tw_notes = st.text_area(
            "Notizen", value="Trinkwasseranalyse 27.03.2025, Labor Kneißler"
        )
        if st.form_submit_button("Speichern"):
            save_trinkwasser(
                session,
                name=tw_name,
                ph_default=tw_ph,
                alkalinity_default=tw_alk,
                calcium_hardness_default=tw_hard,
                notes=tw_notes,
            )
            st.rerun()

with tab3:
    st.subheader("Produkte")
    for prod in get_products(session):
        with st.expander(f"🧪 {prod.name}"):
            with st.form(key=f"prod_{prod.id}"):
                p_name = st.text_input("Name", value=prod.name)
                p_typ = st.selectbox(
                    "Typ",
                    ["ph_minus", "ph_plus", "chlorine"],
                    index=["ph_minus", "ph_plus", "chlorine"].index(prod.typ),
                )
                col1, col2 = st.columns(2)
                with col1:
                    p_factor = st.number_input(
                        "Dosierfaktor", value=prod.dosage_factor, step=0.01
                    )
                with col2:
                    p_unit = st.text_input("Einheit", value=prod.unit)
                p_chlorine = st.number_input(
                    "Aktives Chlor pro Tablette (mg)",
                    value=prod.active_chlorine_per_tab or 0.0,
                    step=0.5,
                )
                p_interval = st.number_input(
                    "Wiederholintervall (Tage, 0 = einmalig)",
                    min_value=0,
                    value=prod.interval_days,
                )
                p_notes = st.text_area("Notizen", value=prod.notes or "")
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("Speichern"):
                        update_product(
                            session,
                            prod.id,
                            name=p_name,
                            typ=p_typ,
                            dosage_factor=p_factor,
                            unit=p_unit,
                            active_chlorine_per_tab=p_chlorine
                            if p_typ == "chlorine" and p_chlorine > 0
                            else None,
                            interval_days=p_interval,
                            notes=p_notes,
                        )
                        st.rerun()
                with col2:
                    if st.form_submit_button("Löschen"):
                        delete_product(session, prod.id)
                        st.rerun()

    st.divider()
    with st.form("new_product"):
        st.subheader("Neues Produkt")
        col1, col2 = st.columns(2)
        with col1:
            np_name = st.text_input("Name")
        with col2:
            np_typ = st.selectbox("Typ", ["ph_minus", "ph_plus", "chlorine"])
        col1, col2 = st.columns(2)
        with col1:
            np_factor = st.number_input("Dosierfaktor", value=0.0, step=0.1)
        with col2:
            np_unit = st.text_input("Einheit", value="g")
        col1, col2 = st.columns(2)
        with col1:
            np_chlorine = st.number_input(
                "Aktives Chlor pro Tablette (mg)", value=0.0, step=0.5
            )
        with col2:
            np_interval = st.number_input(
                "Wiederholintervall (Tage)", min_value=0, value=0
            )
        np_notes = st.text_area("Notizen")
        if st.form_submit_button("Speichern"):
            save_product(
                session,
                name=np_name,
                typ=np_typ,
                dosage_factor=np_factor,
                unit=np_unit,
                active_chlorine_per_tab=np_chlorine
                if np_typ == "chlorine" and np_chlorine > 0
                else None,
                interval_days=np_interval,
                notes=np_notes,
            )
            st.rerun()
