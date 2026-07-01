# Pool Water Balance UI Redesign — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure Wasserrechner.py: add pH/Chlor gauges, reorganize into Hygiene + Kalk-Korrosion sections, move Handlungsbedarf to Dosierempfehlung, add consensus indicator.

**Architecture:** Single-file change to `/app/Wasserrechner.py`. All calculation logic (lsi.py, rsi.py, dosing.py) remains untouched. No new files.

**Tech Stack:** Python 3, Streamlit, Plotly

---

### Task 1: Add pH and Chlor Gauge Charts

**Files:**
- Modify: `/app/Wasserrechner.py` (add gauge functions + render them)

- [ ] **Step 1: Read the current file to understand structure**

Run: `cat -n /app/Wasserrechner.py | head -320`

- [ ] **Step 2: Add helper function for creating target-range gauges**

After the imports (line ~19), add a function to create a standardized gauge:

```python
def _target_gauge(value, title, axis_range, green_zone, unit=""):
    """Create a Plotly gauge with green zone = target range."""
    fig = go.Figure()
    green_min, green_max = green_zone
    steps = [
        {"range": [axis_range[0], green_min], "color": "lightcoral"},
        {"range": [green_min, green_max], "color": "lightgreen"},
        {"range": [green_max, axis_range[1]], "color": "lightcoral"},
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
    fig.update_layout(height=200, margin=dict(l=20, r=20, t=40, b=20))
    return fig
```

- [ ] **Step 3: Render pH and Chlor gauges in Section 2 (replacing old metric display)**

In the current file, replace lines 299-312 (the pH/chlor metric section) with a `🧼 Hygiene` subheader and two gauge columns. Insert this after the LSI/RSI expander (after line 297) and before the divider (line 314):

```python
st.markdown("#### 🧼 Hygiene")
col_ph_gauge, col_chlor_gauge = st.columns(2)
with col_ph_gauge:
    ph_fig = _target_gauge(
        ph, "pH", [6.2, 8.4],
        [pool.ph_min, pool.ph_max]
    )
    st.plotly_chart(ph_fig, use_container_width=True)
    ph_ok = pool.ph_min <= ph <= pool.ph_max
    st.metric(
        "pH",
        f"{ph:.1f}",
        delta="✅ i.O." if ph_ok else f"⚠️ Ziel {pool.ph_min}–{pool.ph_max}",
    )
with col_chlor_gauge:
    chl_fig = _target_gauge(
        chlorine, "Chlor", [0.0, 10.0],
        [pool.chlorine_min, pool.chlorine_max],
        unit="mg/L"
    )
    st.plotly_chart(chl_fig, use_container_width=True)
    chl_ok = pool.chlorine_min <= chlorine <= pool.chlorine_max
    st.metric(
        "Chlor",
        f"{chlorine:.1f} mg/L",
        delta="✅ i.O." if chl_ok else f"⚠️ Ziel {pool.chlorine_min}–{pool.chlorine_max}",
    )
```

- [ ] **Step 4: Run the app to confirm no syntax errors**

Run: `python -c "import py_compile; py_compile.compile('/app/Wasserrechner.py', doraise=True)" && echo "OK"`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add /app/Wasserrechner.py
git commit -m "feat: add pH and Chlor gauge visualizations with _target_gauge helper"
```

---

### Task 2: Restructure Section 2 — Add Consensus Indicator + Kalk-Korrosion Labeling

**Files:**
- Modify: `/app/Wasserrechner.py` (Section 2: Wasserbalance)

- [ ] **Step 1: Read current Section 2 code**

Run: `sed -n '192,297p' /app/Wasserrechner.py`

- [ ] **Step 2: Add "Kalk-Korrosion Gleichgewicht" subheader and consensus indicator**

Replace the old 3-column LSI/RSI/Status section (lines 192-232) with a labeled section that includes a consensus column:

```python
st.markdown("#### ⚖️ Kalk-Korrosion Gleichgewicht")

col_lsi, col_rsi, col_consensus = st.columns(3)

with col_lsi:
    lsi_color = (
        "green" if lsi_cat == "ausgeglichen"
        else ("red" if lsi_cat in ("korrosiv", "kalkend") else "orange")
    )
    lsi_arrow = "✅" if lsi_cat == "ausgeglichen" else ("🔴" if lsi_cat == "korrosiv" else "🟠")
    st.markdown(
        f"### {lsi_arrow} LSI: <span style='color:{lsi_color}'>{lsi:+.2f}</span>",
        unsafe_allow_html=True,
    )

with col_rsi:
    rsi_color = (
        "green" if rsi_cat == "ausgeglichen"
        else ("red" if rsi_cat == "korrosiv" else "orange")
    )
    rsi_arrow = "✅" if rsi_cat == "ausgeglichen" else ("🔴" if rsi_cat == "korrosiv" else "🟠")
    st.markdown(
        f"### {rsi_arrow} RSI: <span style='color:{rsi_color}'>{rsi:.1f}</span>",
        unsafe_allow_html=True,
    )

with col_consensus:
    if lsi_cat == "ausgeglichen" and rsi_cat == "ausgeglichen":
        st.success("✅ Wasser im\nKalk-Gleichgewicht")
    elif lsi_cat == rsi_cat:
        direction = lsi_cat
        if direction == "korrosiv":
            st.warning("⚠️ Beide Indizes zeigen Korrosionstendenz")
        elif direction == "kalkausfällend" or direction == "kalkend":
            st.warning("⚠️ Beide Indizes zeigen Kalktendenz")
    else:
        st.info(
            "ℹ️ Unterschiedliche Tendenz\n\n"
            "LSI und RSI bewerten unterschiedliche Aspekte: "
            "LSI zeigt das Kalkgleichgewicht (Pooloberfläche), "
            "RSI die Korrosionsneigung (Metallteile). "
            "Orientieren Sie sich am LSI. Details & Maßnahmen → Dosierempfehlung."
        )
```

- [ ] **Step 3: Remove old Handlungsbedarf warning** (it's being moved to Task 3)

Confirm lines 218-232 (the old `st.warning("⚡ Handlungsbedarf")` block) have been replaced by the consensus column above.

- [ ] **Step 4: Update the expander content to include richer info about indices**

Replace lines 278-297 with enriched content:

```python
with st.expander("ℹ️ Detailwissen: Wasserbalance-Indizes"):
    st.markdown("""
**LSI (Langelier Sättigungs-Index)** – PHTA-Standard für Kalk-Korrosion.
- **< -0,5 (korrosiv)**: Greift Beckenoberflächen und Rohre an.
- **-0,5 bis +0,5 (ausgeglichen)**: Idealer Bereich.
- **> +0,5 (kalkausfällend)**: Kalkablagerungen.

**RSI (Ryznar Stabilitäts-Index)** – Fokussiert auf Metallschutz.
- **< 6,0 (kalkend)**: Schutzschicht bildend — von Heizungsherstellern bevorzugt.
- **6,0 – 7,0 (ausgeglichen)**: Optimal für die meisten Anlagen.
- **> 7,0 (korrosiv)**: Korrosionsgefahr für Metallteile.

> Ein RSI von 5,0–7,0 entspricht etwa LSI +0,1 bis +1,4. Der RSI ist bewusst
> in Richtung leichter Kalkbildung verschoben, da eine dünne Schutzschicht
> Metallkorrosion verhindert.

**Hamilton Index** – Alternative Methode (Jock Hamilton, 1960er):
- Ziel-pH: 7,8–8,2 (höher als LSI/RSI)
- Steuert Gesamtalkalinität abhängig von Gesamthärte
- Berücksichtigt keine Temperatur, TDS oder Cyanursäure

**Wenn LSI und RSI sich widersprechen:**
Das ist normal. Der LSI bewertet das Kalkgleichgewicht (relevant für
Pooloberflächen), der RSI bewertet die Korrosionsschutzschicht (relevant
für Metallteile). Die aktuellen Maßnahmen helfen in beiden Fällen.

👉 [LSI Rechner & Erklärung (poolplanet.de)](https://www.poolplanet.de/ratgeber/lsi-rechner/)
👉 [Wasserbalance im Pool (wasserfachmann.de)](https://www.wasserfachmann.de/wasserbalance/)
👉 [Hamilton Index Erklärung (United Chemical)](https://www.unitedchemical.com/hamilton-index/)
    """)
```

- [ ] **Step 5: Verify**

Run: `python -c "import py_compile; py_compile.compile('/app/Wasserrechner.py', doraise=True)" && echo "OK"`
Expected: `OK`

- [ ] **Step 6: Commit**

```bash
git add /app/Wasserrechner.py
git commit -m "feat: restructure Section 2 with consensus indicator and enriched index education"
```

---

### Task 3: Move Handlungsbedarf to Section 3 & Restructure Layout

**Files:**
- Modify: `/app/Wasserrechner.py` (move Handlungsbedarf warning to Dosierempfehlung, move save button to Section 1)

- [ ] **Step 1: Read current Section 1 end and Section 3 start**

Run: `sed -n '137,192p' /app/Wasserrechner.py` (photo section + divider)

- [ ] **Step 2: Move the save button to right after photo upload**

Replace lines 172-173 (after photo display) with:

```python
    st.image(photo_data, caption="Hochgeladenes Foto", width=300)

# Save button (moved here for workflow: measure → photo → save)
st.divider()
if st.button("💾 Messung speichern", type="primary", use_container_width=True):
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
            )
    st.success("✅ Messung gespeichert!")
    st.session_state.last_dosing = dosing
    st.session_state.task_created = False
    if "executed_actions" in st.session_state:
        del st.session_state.executed_actions

st.divider()
```

- [ ] **Step 3: Remove the old save button (lines ~387-440)**

Delete the old save button block at the end of Section 3.

- [ ] **Step 4: Add Handlungsbedarf at top of Section 3**

Replace the current Section 3 header (line 317) with:

```python
st.subheader("3️⃣ Dosierempfehlung")

# Handlungsbedarf — synthesized from all diagnostic data
has_hygiene_issue = not ph_ok or not chl_ok
has_kalk_issue = lsi_cat != "ausgeglichen" or rsi_cat != "ausgeglichen"

if has_hygiene_issue or has_kalk_issue:
    st.warning("⚡ Handlungsbedarf")
    if has_hygiene_issue:
        hygiene_tips = []
        if not ph_ok:
            hygiene_tips.append(
                f"pH {ph:.1f} ist außerhalb des Zielbereichs "
                f"({pool.ph_min}–{pool.ph_max})"
            )
        if not chl_ok:
            hygiene_tips.append(
                f"Chlor {chlorine:.1f} mg/L ist außerhalb des Zielbereichs "
                f"({pool.chlorine_min}–{pool.chlorine_max} mg/L)"
            )
        st.markdown(f"**🧼 Hygiene:** {'; '.join(hygiene_tips)}")
    if has_kalk_issue:
        kalk_tips = []
        if lsi_cat == "korrosiv":
            kalk_tips.append("LSI korrosiv → Calciumhärte oder Alkalinität erhöhen")
        elif lsi_cat == "kalkausfällend":
            kalk_tips.append("LSI kalkend → Calciumhärte oder Alkalinität reduzieren")
        if rsi_cat == "korrosiv":
            kalk_tips.append("RSI korrosiv → pH anheben (falls Hygiene-Ziel es erlaubt)")
        elif rsi_cat == "kalkend":
            kalk_tips.append("RSI kalkend → pH senken (falls Hygiene-Ziel es erlaubt)")
        st.markdown(
            f"**⚖️ Kalk-Korrosion:** {'; '.join(kalk_tips)}"
            if kalk_tips
            else f"**⚖️ Kalk-Korrosion:** Siehe Detailwissen oben"
        )
else:
    st.success("✅ Alles im grünen Bereich — keine Maßnahmen nötig.")
```

Then continue with the existing dosing recommendation loop (starting from `if dosing:`).

- [ ] **Step 5: Remove the old divider between old Section 2 and Section 3** (the `st.divider()` at line 314)

Remove line 314 (`st.divider()`) since we now have a clear section break.

- [ ] **Step 6: Remove the last divider and last saved result expander**

Remove lines 384-455 (the second `st.divider()`, old save button, "Letzte gespeicherte Messung" expander).

- [ ] **Step 7: Verify**

Run: `python -c "import py_compile; py_compile.compile('/app/Wasserrechner.py', doraise=True)" && echo "OK"`
Expected: `OK`

- [ ] **Step 8: Commit**

```bash
git add /app/Wasserrechner.py
git commit -m "feat: move save button to Section 1, move Handlungsbedarf to Section 3"
```

---

### Task 4: Update Existing Tests

**Files:**
- Read: `/app/tests/test_lsi.py`
- Read: `/app/tests/test_rsi.py`
- Read: `/app/tests/test_dosing.py`

- [ ] **Step 1: Run existing tests to ensure nothing broke**

Run: `python -m pytest tests/ -v`
Expected: All existing tests pass (the calculation logic hasn't changed)

- [ ] **Step 2: Commit if any test adjustments were needed**

```bash
git add tests/
git commit -m "test: update tests for UI restructure"
```
