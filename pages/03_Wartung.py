import datetime
import streamlit as st
from database.db import get_engine, init_db, get_session
from utils.theme import inject_theme
from utils.nav import render_sidebar
from database.repository import (
    get_pools,
    get_pending_tasks,
    complete_task_with_notes,
    save_task,
    get_pending_tasks_for_pool,
    get_active_templates_for_pool,
    ensure_template_instances,
    get_task_templates,
    get_pool_task_defaults,
    set_pool_template_active,
)
from database.models import Product, TaskTemplate, PoolTaskDefault, MaintenanceTask

st.set_page_config(
    page_title="PoolPilot - Dein intelligenter Pool-Helfer", page_icon="🏊"
)
inject_theme()

engine = get_engine()
init_db(engine)
session = get_session(engine)

pools = get_pools(session)
render_sidebar(pools)

st.title("✅ Aufgaben")

selected_pool_id = st.session_state.get("pool_selector", 0)
pool_filter = None if selected_pool_id == 0 else selected_pool_id

today = datetime.date.today()
ensure_template_instances(session, pool_filter or 0, today, today + datetime.timedelta(days=90))

tab1, tab2 = st.tabs(["✅ Aufgaben", "📋 Vorlagen"])

with tab1:
    st.subheader("⚡ Schnell-Aufgabe")
    templates_to_show = get_active_templates_for_pool(session, pool_filter) if pool_filter else []
    if not pool_filter and pools:
        templates_to_show = get_active_templates_for_pool(session, pools[0].id)

    if templates_to_show:
        categories = {}
        for t in templates_to_show:
            cat = t.category or "allgemein"
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(t)

        cat_labels = {"chemie": "🧪 Chemie", "technik": "🔧 Technik", "reinigung": "🧹 Reinigung", "allgemein": "📋 Allgemein"}
        for cat, tmpls in categories.items():
            label = cat_labels.get(cat, cat)
            cols = st.columns(len(tmpls))
            for i, tmpl in enumerate(tmpls):
                with cols[i]:
                    if st.button(f"{tmpl.icon} {tmpl.name}", key=f"qa_{tmpl.id}", use_container_width=True):
                        target_pool_id = pool_filter or (pools[0].id if pools else None)
                        rec_amount = None
                        rec_unit = None
                        if tmpl.product_id:
                            product = session.query(Product).filter(Product.id == tmpl.product_id).first()
                            if product and product.dosage_factor > 0 and target_pool_id:
                                p = next((p for p in pools if p.id == target_pool_id), None)
                                if p:
                                    volume_m3 = p.volume_liter / 1000
                                    rec_amount = round(product.dosage_factor * volume_m3, 1)
                                    rec_unit = product.unit
                        save_task(
                            session,
                            task_type="template",
                            title=tmpl.name,
                            description=tmpl.description or "",
                            due_date=today,
                            interval_days=tmpl.interval_days,
                            template_id=tmpl.id,
                            pool_id=target_pool_id,
                            product_id=tmpl.product_id,
                            product_name=tmpl.product_name,
                            recommended_amount=rec_amount,
                            recommended_unit=rec_unit,
                        )
                        st.rerun()
    else:
        st.caption("Keine Vorlagen aktiv. In Poolverwaltung aktivieren.")

    st.divider()

    if pool_filter:
        tasks = get_pending_tasks_for_pool(session, pool_filter)
    else:
        tasks = get_pending_tasks(session)

    if not tasks:
        st.success("✅ Alle Aufgaben erledigt!")
    else:
        for task in tasks:
            overdue = task.due_date and task.due_date < today
            is_today = task.due_date == today
            if overdue:
                icon = "🔴"
            elif is_today:
                icon = "🟡"
            else:
                icon = "🟢"

            with st.container(border=True):
                cols = st.columns([3, 1, 2])
                with cols[0]:
                    st.write(f"{icon} **{task.title}**")
                    if task.description:
                        st.caption(task.description)
                    if task.completed_at:
                        st.caption(
                            f"✅ Erledigt: {task.completed_at.strftime('%d.%m.%Y %H:%M')}"
                        )
                    if task.recommended_amount is not None:
                        st.caption(f"Empfohlen: {task.recommended_amount:g} {task.recommended_unit or ''}")
                with cols[1]:
                    if task.due_date:
                        label = (
                            "Überfällig!"
                            if overdue
                            else ("Heute" if is_today else task.due_date.strftime("%d.%m.%Y"))
                        )
                        st.write(f"Fällig: {label}")
                    if task.interval_days:
                        st.caption(f"Alle {task.interval_days} Tage")
                    if task.follow_up_days:
                        st.caption(f"Folge in {task.follow_up_days} Tagen")
                with cols[2]:
                    if not task.completed:
                        exec_notes = st.text_input(
                            "Doku",
                            placeholder="z. B. 100g zugegeben",
                            key=f"exec_{task.id}",
                        )
                        actual_amount = None
                        actual_unit = task.recommended_unit
                        if task.recommended_amount is not None:
                            actual_amount = st.number_input(
                                "Tatsächliche Dosis",
                                value=task.recommended_amount,
                                step=0.1,
                                key=f"amt_{task.id}",
                                label_visibility="collapsed",
                                placeholder=f"Menge ({actual_unit or 'g'})",
                            )
                        if st.button(
                            "✅ Erledigt", key=f"done_{task.id}", use_container_width=True
                        ):
                            complete_task_with_notes(
                                session, task.id,
                                executed_notes=exec_notes,
                                actual_amount=actual_amount,
                                actual_unit=actual_unit,
                            )
                            st.rerun()

    st.divider()

    with st.expander("➕ Manuelle Aufgabe"):
        with st.form("manuelle_aufgabe"):
            pools_for_new = {p.id: p.name for p in pools}
            sel_pool_id = st.selectbox(
                "Pool",
                options=list(pools_for_new.keys()),
                format_func=lambda x: pools_for_new[x],
            )
            title = st.text_input("Titel")
            description = st.text_area("Beschreibung")
            due_date = st.date_input("Fällig am", value=today)
            interval = st.number_input(
                "Wiederholen alle (Tage, 0 = einmalig)", min_value=0, value=0
            )
            follow_up = st.number_input(
                "Folgeaufgabe in (Tagen, 0 = keine)", min_value=0, value=0
            )
            if st.form_submit_button("Speichern"):
                save_task(
                    session,
                    task_type="custom",
                    title=title,
                    description=description,
                    due_date=due_date,
                    interval_days=interval,
                )
                if follow_up > 0:
                    save_task(
                        session,
                        task_type="custom",
                        title=f"{title} (Folge)",
                        description=f"Folgeaufgabe in {follow_up} Tagen",
                        due_date=due_date + datetime.timedelta(days=follow_up),
                        interval_days=0,
                    )
                st.success("Aufgabe gespeichert!")
                st.rerun()

with tab2:
    st.subheader("📋 Vorlagen verwalten")
    all_templates = get_task_templates(session)
    cat_labels = {"chemie": "🧪 Chemie", "technik": "🔧 Technik", "reinigung": "🧹 Reinigung", "allgemein": "📋 Allgemein"}

    products = session.query(Product).order_by(Product.name).all()

    with st.expander("➕ Neue Vorlage", expanded=False):
        with st.form("new_template"):
            t_name = st.text_input("Name", placeholder="z.B. Filter rückspülen")
            t_icon = st.text_input("Icon (Emoji)", value="📋", max_chars=5)
            t_category = st.selectbox("Kategorie", options=["chemie", "technik", "reinigung", "allgemein"], format_func=lambda x: cat_labels.get(x, x))
            t_interval = st.number_input("Intervall (Tage, 0 = einmalig)", min_value=0, value=7)
            t_pool_type = st.selectbox("Pool-Typ", options=["all", "chlorine", "bromine"])
            t_follow_up = st.number_input("Folgeaufgabe (Tage, 0 = keine)", min_value=0, value=0)
            t_description = st.text_area("Beschreibung (optional)")
            product_options = {0: "— Kein Produkt —"} | {p.id: p.name for p in products}
            t_product_id = st.selectbox("Produkt (optional)", options=list(product_options.keys()), format_func=lambda x: product_options[x])
            if st.form_submit_button("💾 Speichern"):
                product_id = t_product_id if t_product_id > 0 else None
                product_name = None
                if product_id:
                    prod = session.query(Product).filter(Product.id == product_id).first()
                    product_name = prod.name if prod else None
                session.add(TaskTemplate(
                    name=t_name, icon=t_icon, category=t_category,
                    interval_days=t_interval, pool_type=t_pool_type,
                    default_follow_up_days=t_follow_up, description=t_description,
                    product_id=product_id, product_name=product_name,
                ))
                session.commit()
                st.success(f"Vorlage '{t_name}' erstellt!")
                st.rerun()

    st.divider()

    cat_order = ["chemie", "technik", "reinigung", "allgemein"]
    for cat in cat_order:
        cat_templates = [t for t in all_templates if (t.category or "allgemein") == cat]
        if not cat_templates:
            continue
        st.markdown(f"**{cat_labels.get(cat, cat)}**")
        for tmpl in cat_templates:
            cols = st.columns([1, 3, 1, 1])
            with cols[0]:
                st.write(tmpl.icon or "📋")
            with cols[1]:
                st.write(f"**{tmpl.name}**")
                details = f"Alle {tmpl.interval_days} Tage" if tmpl.interval_days else "Einmalig"
                if tmpl.product_name:
                    details += f" · {tmpl.product_name}"
                st.caption(details)
            with cols[2]:
                st.write(f"`{tmpl.pool_type or 'all'}`")

            edit_key = f"edit_{tmpl.id}"
            if st.button("✏️", key=f"edit_btn_{tmpl.id}", help="Bearbeiten"):
                st.session_state[edit_key] = not st.session_state.get(edit_key, False)

            del_key = f"del_{tmpl.id}"
            if st.button("🗑️", key=f"del_btn_{tmpl.id}", help="Löschen"):
                st.session_state[del_key] = True

            if st.session_state.get(del_key, False):
                st.warning(f"Vorlage '{tmpl.name}' wirklich löschen?")
                if st.button("Ja, löschen", key=f"confirm_del_{tmpl.id}"):
                    session.query(MaintenanceTask).filter(
                        MaintenanceTask.template_id == tmpl.id
                    ).update({MaintenanceTask.template_id: None})
                    session.query(PoolTaskDefault).filter(
                        PoolTaskDefault.template_id == tmpl.id
                    ).delete()
                    session.delete(tmpl)
                    session.commit()
                    st.session_state[del_key] = False
                    st.rerun()
                if st.button("Abbrechen", key=f"cancel_del_{tmpl.id}"):
                    st.session_state[del_key] = False
                    st.rerun()

            if st.session_state.get(edit_key, False):
                with st.form(key=f"edit_form_{tmpl.id}"):
                    e_name = st.text_input("Name", value=tmpl.name)
                    e_icon = st.text_input("Icon", value=tmpl.icon or "📋", max_chars=5)
                    e_category = st.selectbox(
                        "Kategorie", options=["chemie", "technik", "reinigung", "allgemein"],
                        index=["chemie", "technik", "reinigung", "allgemein"].index(tmpl.category or "allgemein"),
                        format_func=lambda x: cat_labels.get(x, x),
                    )
                    e_interval = st.number_input("Intervall (Tage)", min_value=0, value=tmpl.interval_days or 7)
                    e_pool_type = st.selectbox("Pool-Typ", options=["all", "chlorine", "bromine"], index=["all", "chlorine", "bromine"].index(tmpl.pool_type or "all"))
                    e_follow_up = st.number_input("Folgeaufgabe (Tage)", min_value=0, value=tmpl.default_follow_up_days or 0)
                    e_description = st.text_area("Beschreibung", value=tmpl.description or "")
                    product_options = {0: "— Kein Produkt —"} | {p.id: p.name for p in products}
                    e_product_id = st.selectbox(
                        "Produkt", options=list(product_options.keys()),
                        index=list(product_options.keys()).index(tmpl.product_id if tmpl.product_id else 0),
                        format_func=lambda x: product_options[x],
                    )
                    if st.form_submit_button("💾 Speichern"):
                        tmpl.name = e_name
                        tmpl.icon = e_icon
                        tmpl.category = e_category
                        tmpl.interval_days = e_interval
                        tmpl.pool_type = e_pool_type
                        tmpl.default_follow_up_days = e_follow_up
                        tmpl.description = e_description
                        tmpl.product_id = e_product_id if e_product_id > 0 else None
                        session.commit()
                        st.session_state[edit_key] = False
                        st.success("Gespeichert!")
                        st.rerun()

    st.divider()

    st.subheader("🔘 Pro-Pool Aktivierung")
    for pool in pools:
        with st.expander(f"🏊 {pool.name}", expanded=False):
            defaults = {ptd.template_id: ptd for ptd in get_pool_task_defaults(session, pool.id)}
            for tmpl in all_templates:
                ptd = defaults.get(tmpl.id)
                active = ptd.active if ptd else False
                key = f"pool_{pool.id}_tmpl_{tmpl.id}"
                new_active = st.checkbox(f"{tmpl.icon or '📋'} {tmpl.name}", value=active, key=key)
                if new_active != active:
                    set_pool_template_active(session, pool.id, tmpl.id, new_active)
                    st.rerun()
