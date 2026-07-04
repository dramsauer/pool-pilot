# Default Tasks & Vorlagen-Verwaltung Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add 12 default task templates to config.toml so they seed into the DB, and add a Vorlagen-CRUD tab to the Wartung page.

**Architecture:** Phase A: TOML config section that feeds existing `_seed_task_templates()` in db.py. Phase B: Streamlit tabs in 03_Wartung.py — existing task UI stays in Tab 1, new template CRUD in Tab 2.

**Tech Stack:** Python, Streamlit, SQLAlchemy, TOML

---

### Task 1: Add `[task_defaults]` to config.toml

**Files:**
- Modify: `config.toml` (append at end)

- [ ] **Step 1: Add [task_defaults] section to config.toml**

Append at end of `config.toml`:

```toml
[task_defaults]
templates = [
  { name = "Hygiene-Messung (pH/Chlor)", category = "chemie", interval_days = 7, pool_type = "all", icon = "🧪" },
  { name = "Vollanalyse (alle Werte)", category = "chemie", interval_days = 14, pool_type = "all", icon = "📊" },
  { name = "Chlor Tablette zugeben", category = "chemie", interval_days = 7, pool_type = "chlorine", icon = "💊", product_name = "Summer Fun Perfect Care Tabs 20g" },
  { name = "Schockchlorung", category = "chemie", interval_days = 28, pool_type = "chlorine", icon = "⚡" },
  { name = "Filter rückspülen", category = "technik", interval_days = 14, pool_type = "all", icon = "🔄" },
  { name = "Filterpatrone reinigen", category = "technik", interval_days = 7, pool_type = "all", icon = "🧽" },
  { name = "Pumpenvorsieb reinigen", category = "technik", interval_days = 7, pool_type = "all", icon = "🔧" },
  { name = "Skimmer reinigen", category = "reinigung", interval_days = 7, pool_type = "all", icon = "🧹" },
  { name = "Poolboden saugen", category = "reinigung", interval_days = 14, pool_type = "all", icon = "🫧" },
  { name = "Abdeckung reinigen", category = "reinigung", interval_days = 14, pool_type = "all", icon = "🛡️" },
  { name = "Wasserstand prüfen", category = "allgemein", interval_days = 7, pool_type = "all", icon = "📏" },
  { name = "Wasserwechsel (Teilweise)", category = "allgemein", interval_days = 28, pool_type = "all", icon = "💧" },
]
```

- [ ] **Step 2: Verify config.toml is valid TOML**

Run: `python3 -c "import tomllib; f=open('config.toml','rb'); print(len(tomllib.load(f)['task_defaults']['templates']), 'templates loaded')"`
Expected: `12 templates loaded`

- [ ] **Step 3: Commit**

```bash
git add config.toml
git commit -m "feat: add 12 default task templates to config.toml"
```

---

### Task 2: Add Vorlagen-Tab to Wartung page

**Files:**
- Modify: `pages/03_Wartung.py` (entire file — refactor to use tabs, add template CRUD)

- [ ] **Step 1: Read current 03_Wartung.py**

```bash
cat pages/03_Wartung.py
```

Verify understanding of current structure before editing.

- [ ] **Step 2: Rewrite 03_Wartung.py with tabs and template CRUD**

Replace entire file with:

```python
import datetime
import streamlit as st
from database.db import get_engine, init_db, get_session
from database.models import TaskTemplate, PoolTaskDefault
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
    activate_defaults_for_pool,
)
from database.models import Product

st.set_page_config(
    page_title="PoolPilot - Dein intelligenter Pool-Helfer", page_icon="🏊"
)

engine = get_engine()
init_db(engine)
session = get_session(engine)

st.title("✅ Aufgaben")

tab1, tab2 = st.tabs(["✅ Aufgaben", "📋 Vorlagen"])

with tab1:
    # Pool filter
    pools = get_pools(session)
    pool_filter = None
    if len(pools) > 1:
        pool_options = {0: "Alle Pools"} | {p.id: p.name for p in pools}
        selected = st.selectbox(
            "Pool filtern",
            options=list(pool_options.keys()),
            format_func=lambda x: pool_options[x],
        )
        if selected:
            pool_filter = selected

    today = datetime.date.today()
    ensure_template_instances(session, pool_filter or 0, today, today + datetime.timedelta(days=90))

    # Quick-add
    st.subheader("⚡ Schnell-Aufgabe")
    templates_to_show = get_active_templates_for_pool(session, pool_filter) if pool_filter else []
    if not pool_filter and pools:
        templates_to_show = get_active_templates_for_pool(session, pools[0].id)

    if templates_to_show:
        categories: dict[str, list] = {}
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

    # Task list
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

    # Manual task creation
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

    # Template CRUD form
    with st.expander("➕ Neue Vorlage", expanded=False):
        with st.form("new_template"):
            t_name = st.text_input("Name", placeholder="z.B. Filter rückspülen")
            t_icon = st.text_input("Icon (Emoji)", value="📋", max_chars=5)
            t_category = st.selectbox(
                "Kategorie",
                options=["chemie", "technik", "reinigung", "allgemein"],
                format_func=lambda x: cat_labels.get(x, x),
            )
            t_interval = st.number_input("Intervall (Tage, 0 = einmalig)", min_value=0, value=7)
            t_pool_type = st.selectbox("Pool-Typ", options=["all", "chlorine", "bromine"])
            t_follow_up = st.number_input("Folgeaufgabe (Tage, 0 = keine)", min_value=0, value=0)
            t_description = st.text_area("Beschreibung (optional)")
            products = session.query(Product).order_by(Product.name).all()
            product_options = {0: "— Kein Produkt —"} | {p.id: p.name for p in products}
            t_product_id = st.selectbox(
                "Produkt (optional)",
                options=list(product_options.keys()),
                format_func=lambda x: product_options[x],
            )

            if st.form_submit_button("💾 Speichern"):
                product_id = t_product_id if t_product_id > 0 else None
                product_name = None
                if product_id:
                    prod = session.query(Product).filter(Product.id == product_id).first()
                    product_name = prod.name if prod else None
                new_tmpl = TaskTemplate(
                    name=t_name,
                    icon=t_icon,
                    category=t_category,
                    interval_days=t_interval,
                    pool_type=t_pool_type,
                    default_follow_up_days=t_follow_up,
                    description=t_description,
                    product_id=product_id,
                    product_name=product_name,
                )
                session.add(new_tmpl)
                session.commit()
                st.success(f"Vorlage '{t_name}' erstellt!")
                st.rerun()

    st.divider()

    # Template table with edit/delete
    cat_order = ["chemie", "technik", "reinigung", "allgemein"]
    for cat in cat_order:
        cat_templates = [t for t in all_templates if (t.category or "allgemein") == cat]
        if not cat_templates:
            continue
        st.markdown(f"**{cat_labels.get(cat, cat)}**")
        for tmpl in cat_templates:
            cols = st.columns([1, 3, 1, 1, 1])
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
            if st.button("✏️", key=f"edit_btn_{tmpl.id}"):
                st.session_state[edit_key] = not st.session_state.get(edit_key, False)

            if st.button("🗑️", key=f"del_{tmpl.id}"):
                session.delete(tmpl)
                session.commit()
                st.rerun()

            if st.session_state.get(edit_key, False):
                with st.form(key=f"edit_form_{tmpl.id}"):
                    e_name = st.text_input("Name", value=tmpl.name)
                    e_icon = st.text_input("Icon", value=tmpl.icon or "📋", max_chars=5)
                    e_interval = st.number_input("Intervall", min_value=0, value=tmpl.interval_days or 7)
                    e_pool_type = st.selectbox(
                        "Pool-Typ",
                        options=["all", "chlorine", "bromine"],
                        index=["all", "chlorine", "bromine"].index(tmpl.pool_type or "all"),
                    )
                    if st.form_submit_button("💾 Speichern"):
                        tmpl.name = e_name
                        tmpl.icon = e_icon
                        tmpl.interval_days = e_interval
                        tmpl.pool_type = e_pool_type
                        session.commit()
                        st.session_state[edit_key] = False
                        st.success("Gespeichert!")
                        st.rerun()

    st.divider()

    # Per-pool activation
    st.subheader("🔘 Pro-Pool Aktivierung")
    pools = get_pools(session)
    all_templates = get_task_templates(session)
    for pool in pools:
        with st.expander(f"🏊 {pool.name}", expanded=False):
            defaults = {ptd.template_id: ptd for ptd in get_pool_task_defaults(session, pool.id)}
            changed = False
            for tmpl in all_templates:
                ptd = defaults.get(tmpl.id)
                active = ptd.active if ptd else True
                key = f"pool_{pool.id}_tmpl_{tmpl.id}"
                new_active = st.checkbox(
                    f"{tmpl.icon or '📋'} {tmpl.name}",
                    value=active,
                    key=key,
                )
                if new_active != active:
                    set_pool_template_active(session, pool.id, tmpl.id, new_active)
                    changed = True
            if changed:
                st.rerun()
```

- [ ] **Step 3: Verify the app starts without errors**

Run: `python3 -c "import streamlit; print('OK')"` to verify environment.
Then run the app: `streamlit run Wasserrechner.py --server.port 8501 &` and check for startup errors.

- [ ] **Step 4: Commit**

```bash
git add pages/03_Wartung.py
git commit -m "feat: add Vorlagen-CRUD tab to Wartung page"
```
