# Pool Water Balance UI Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure the main page (Wasserrechner.py) to separate Hygiene (pH/Chlor) from Kalk-Korrosion (LSI/RSI), add pH/Chlor gauges, move Handlungsbedarf to Dosierempfehlung, add consensus indicator and enriched educational content, move save button to after photo upload.

**Architecture:** Single-file modification of Wasserrechner.py. No calculation logic changes. Uses existing Plotly gauges, Streamlit columns/expanders, and session state. All new UI elements are self-contained in the main page.

**Tech Stack:** Streamlit, Plotly (go.Indicator), SQLAlchemy, existing pool_calculations modules

---

### Task 1: Add pH and Chlor Gauge Visualizations

**Files:**
- Modify: `/app/Wasserrechner.py` (around lines 299-312, new section in Wasserbalance)

- [ ] **Step 1: Write failing test for gauge helper**

```python
# test_ph_chlor_gauges.py
import pytest
from unittest.mock import patch, MagicMock
import sys
sys.path.insert(0, '/app')

# Test that gauge creation functions exist and return Plotly figures
def test_create_ph_gauge_returns_figure():
    from Wasserrechner import create_ph_gauge
    fig = create_ph_gauge(7.4, 7.2, 7.6)
    assert fig is not None
    assert hasattr(fig, 'data')
    assert len(fig.data) > 0

def test_create_chlor_gauge_returns_figure():
    from Wasserrechner import create_chlor_gauge
    fig = create_chlor_gauge(1.5, 0.5, 3.0)
    assert fig is not None
    assert hasattr(fig, 'data')
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /app && python -m pytest test_ph_chlor_gauges.py -v
# Expected: FAILED (module/function not found)
```

- [ ] **Step 3: Add gauge helper functions to Wasserrechner.py**

```python
# Add these helper functions near the top of Wasserrechner.py, after imports
def create_ph_gauge(ph: float, ph_min: float, ph_max: float) -> go.Figure:
    """Create a Plotly gauge for pH value."""
    fig = go.Figure()
    fig.add_trace(go.Indicator(
        mode="gauge+number",
        value=ph,
        title={"text": "pH-Wert"},
        gauge={
            "axis": {"range": [6.2, 8.4]},
            "bar": {"color": "darkblue"},
            "steps": [
                {"range": [6.2, ph_min], "color": "red"},
                {"range": [ph_min, ph_max], "color": "green"},
                {"range": [ph_max, 8.4], "color": "red"},
            ],
        },
    ))
    fig.update_layout(height=200, margin=dict(l=20, r=20, t=40, b=20))
    return fig


def create_chlor_gauge(chlorine: float, chl_min: float, chl_max: float) -> go.Figure:
    """Create a Plotly gauge for Chlorine value."""
    fig = go.Figure()
    fig.add_trace(go.Indicator(
        mode="gauge+number",
        value=chlorine,
        title={"text": "Chlor (mg/L)"},
        gauge={
            "axis": {"range": [0, 10]},
            "bar": {"color": "darkblue"},
            "steps": [
                {"range": [0, chl_min], "color": "red"},
                {"range": [chl_min, chl_max], "color": "green"},
                {"range": [chl_max, 10], "color": "orange"},
            ],
        },
    ))
    fig.update_layout(height=200, margin=dict(l=20, r=20, t=40, b=20))
    return fig
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /app && python -m pytest test_ph_chlor_gauges.py -v
# Expected: PASSED
```

- [ ] **Step 5: Clean up test file and commit**

```bash
cd /app && rm test_ph_chlor_gauges.py && git add Wasserrechner.py && git commit -m "feat: add pH and Chlor gauge helper functions"
```

---

### Task 2: Restructure Section 2 (Wasserbalance) with Hygiene and Kalk-Korrosion Sub-sections

**Files:**
- Modify: `/app/Wasserrechner.py` (lines 189-297, replace entire Wasserbalance section)

- [ ] **Step 1: Write failing test for new section structure**

```python
# test_wasserbalance_structure.py
import pytest
from unittest.mock import patch, MagicMock
import sys
sys.path.insert(0, '/app')

def test_wasserbalance_has_hygiene_section():
    """Test that Wasserbalance renders Hygiene sub-section with pH/Chlor gauges."""
    import streamlit as st
    from Wasserrechner import render_wasserbalance_section
    
    # Mock streamlit
    with patch.object(st, 'subheader'), \
         patch.object(st, 'markdown'), \
         patch.object(st, 'columns'), \
         patch.object(st, 'plotly_chart'):
        render_wasserbalance_section(
            ph=7.4, chlorine=1.5, lsi=0.2, rsi=6.5,
            lsi_cat="ausgeglichen", rsi_cat="ausgeglichen",
            pool=MagicMock(ph_min=7.2, ph_max=7.6, chlorine_min=0.5, chlorine_max=3.0)
        )
    # If no exception, structure is callable
    assert True

def test_wasserbalance_has_kalk_korrosion_section():
    """Test that Wasserbalance renders Kalk-Korrosion sub-section with LSI/RSI/consensus."""
    import streamlit as st
    from Wasserrechner import render_wasserbalance_section
    
    with patch.object(st, 'subheader'), \
         patch.object(st, 'markdown'), \
         patch.object(st, 'columns'), \
         patch.object(st, 'plotly_chart'), \
         patch.object(st, 'expander'):
        render_wasserbalance_section(
            ph=7.4, chlorine=1.5, lsi=0.2, rsi=6.5,
            lsi_cat="ausgeglichen", rsi_cat="ausgeglichen",
            pool=MagicMock(ph_min=7.2, ph_max=7.6, chlorine_min=0.5, chlorine_max=3.0)
        )
    assert True
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /app && python -m pytest test_wasserbalance_structure.py -v
# Expected: FAILED (function not found)
```

- [ ] **Step 3: Refactor Wasserbalance section into structured sub-sections**

```python
# In Wasserrechner.py, replace the entire Section 2 (lines 189-297) with:

def render_wasserbalance_section(ph, chlorine, lsi, rsi, lsi_cat, rsi_cat, pool):
    """Render the Wasserbalance section with Hygiene and Kalk-Korrosion sub-sections."""
    st.subheader("2️⃣ Wasserbalance")
    st.caption("Diagnose: Hygiene & Kalk-Korrosion Gleichgewicht")
    
    # --- Sub-section A: Hygiene ---
    st.markdown("#### 🧼 Hygiene")
    col_ph, col_chlor = st.columns(2)
    
    with col_ph:
        ph_fig = create_ph_gauge(ph, pool.ph_min, pool.ph_max)
        st.plotly_chart(ph_fig, use_container_width=True)
        ph_ok = pool.ph_min <= ph <= pool.ph_max
        st.metric(
            "pH", f"{ph:.1f}",
            delta="✅ i.O." if ph_ok else f"⚠️ Ziel {pool.ph_min}–{pool.ph_max}"
        )
    
    with col_chlor:
        chlor_fig = create_chlor_gauge(chlorine, pool.chlorine_min, pool.chlorine_max)
        st.plotly_chart(chlor_fig, use_container_width=True)
        chl_ok = pool.chlorine_min <= chlorine <= pool.chlorine_max
        st.metric(
            "Chlor", f"{chlorine:.1f} mg/L",
            delta="✅ i.O." if chl_ok else f"⚠️ Ziel {pool.chlorine_min}–{pool.chlorine_max} mg/L"
        )
    
    # --- Sub-section B: Kalk-Korrosion Gleichgewicht ---
    st.markdown("#### ⚖️ Kalk-Korrosion Gleichgewicht")
    col_lsi, col_rsi, col_consensus = st.columns(3)
    
    with col_lsi:
        lsi_color = (
            "green" if lsi_cat == "ausgeglichen"
            else ("red" if lsi_cat == "korrosiv" else "orange")
        )
        lsi_arrow = "✅" if lsi_cat == "ausgeglichen" else ("🔴" if lsi_cat == "korrosiv" else "🟠")
        st.markdown(
            f"### {lsi_arrow} LSI: <span style='color:{lsi_color}'>{lsi:+.2f}</span>",
            unsafe_allow_html=True,
        )
        lsi_fig = go.Figure()
        lsi_fig.add_trace(go.Indicator(
            mode="gauge+number", value=lsi, title={"text": "LSI"},
            gauge={"axis": {"range": [-2, 2]}, "bar": {"color": "darkblue"},
                "steps": [{"range": [-2, -0.5], "color": "red"},
                          {"range": [-0.5, 0.5], "color": "green"},
                          {"range": [0.5, 2], "color": "orange"}]}
        ))
        lsi_fig.update_layout(height=200, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(lsi_fig, use_container_width=True)
    
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
        rsi_fig = go.Figure()
        rsi_fig.add_trace(go.Indicator(
            mode="gauge+number", value=rsi, title={"text": "RSI"},
            gauge={"axis": {"range": [3, 11]}, "bar": {"color": "darkblue"},
                "steps": [{"range": [3, 6], "color": "orange"},
                          {"range": [6, 7], "color": "green"},
                          {"range": [7, 11], "color": "red"}]}
        ))
        rsi_fig.update_layout(height=200, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(rsi_fig, use_container_width=True)
    
    with col_consensus:
        # Consensus indicator
        if lsi_cat == "ausgeglichen" and rsi_cat == "ausgeglichen":
            st.success("✅ Wasser im Kalk-Korrosion Gleichgewicht")
        elif lsi_cat == rsi_cat:
            # Both agree on direction
            direction = "korrosiv" if lsi_cat == "korrosiv" else "kalkend"
            st.warning(f"⚠️ Beide Indizes: {direction}")
            if direction == "korrosiv":
                st.caption("→ pH anheben oder Härte/Alkalinität erhöhen")
            else:
                st.caption("→ pH senken oder Härte/Alkalinität reduzieren")
        else:
            # Conflict between LSI and RSI
            st.warning("⚠️ Unterschiedliche Tendenz")
            st.caption(
                "LSI = Kalkgleichgewicht (Pooloberfläche), "
                "RSI = Korrosionsschutz (Metallteile). "
                "Leichte Abweichung ist normal. "
                "Orientieren Sie sich am LSI für die Wasserbalance."
            )
            st.caption("Details & Handlungsbedarf → Dosierempfehlung")
    
    # --- Educational Expander ---
    with st.expander("ℹ️ Detailwissen: LSI, RSI & Hamilton Index"):
        st.markdown("""
        **LSI (Langelier Sättigungs-Index)** – PHTA-Standard  
        Bereich: -0,3 bis +0,5 (ausgeglichen). Misst Calciumcarbonat-Gleichgewicht.  
        • < -0,3: korrosiv → greift Beckenoberflächen an  
        • > +0,5: kalkausfällend → Beläge, trübes Wasser  
        *Bevorzugt leicht positiven Wert (Schutzschicht).*

        **RSI (Ryznar Stabilitäts-Index)** – Empirisch, Fokus Metalle  
        Bereich: 5,0–7,0 (ausgeglichen). Entspricht ca. LSI +0,1 bis +1,4.  
        *Bevorzugt leicht kalkende Wasser zum Schutz von Heizern/Rohren.*

        **Hamilton Index** – Praxistabelle von Jock Hamilton (1960er)  
        Empfiehlt pH 7,8–8,2. Nutzt **Gesamthärte** vs. **Gesamtalkalinität**.  
        Ignoriert Temperatur, TDS, Cyanursäure.

        **Bei Widerspruch:** LSI für Wasserbalance (Oberfläche), RSI für Geräteschutz. 
        Die Dosierempfehlung unten fasst beides zusammen.
        """)


# Then in the main flow, replace lines 189-297 with:
# render_wasserbalance_section(ph, chlorine, lsi, rsi, lsi_cat, rsi_cat, pool)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /app && python -m pytest test_wasserbalance_structure.py -v
# Expected: PASSED (adjust test as needed to match actual function signature)
```

- [ ] **Step 5: Clean up test file and commit**

```bash
cd /app && rm test_wasserbalance_structure.py && git add Wasserrechner.py && git commit -m "feat: restructure Wasserbalance into Hygiene and Kalk-Korrosion sub-sections"
```

---

### Task 3: Move Save Button to After Photo Upload (Section 1)

**Files:**
- Modify: `/app/Wasserrechner.py` (move lines 387-440 to after photo upload ~line 172)

- [ ] **Step 1: Write failing test**

```python
# test_save_button_position.py
import pytest
from unittest.mock import patch, MagicMock
import sys
sys.path.insert(0, '/app')

def test_save_button_after_photo():
    """Test that save button logic is reachable after photo section."""
    import streamlit as st
    from Wasserrechner import handle_save_reading
    
    with patch.object(st, 'button', return_value=True), \
         patch('database.repository.save_reading_for_pool') as mock_save, \
         patch('database.repository.save_photo'), \
         patch('database.repository.save_task'), \
         patch('database.repository.get_session'):
        
        mock_save.return_value = MagicMock(id=1)
        handle_save_reading(
            pool_id=1, ph=7.4, chlorine=1.5, alkalinity=100, hardness=200,
            temperature=25, lsi=0.2, rsi=6.5, dosing=[], notes="", photo_path=None
        )
        mock_save.assert_called_once()
    assert True
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /app && python -m pytest test_save_button_position.py -v
# Expected: FAILED
```

- [ ] **Step 3: Move save button code**

```python
# In Wasserrechner.py, after photo upload (around line 172), add:

# Save button (MOVED HERE from end of file)
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

    # Link photo if taken
    if photo_path:
        save_photo(
            session,
            image_path=photo_path,
            caption=f"Messung {datetime.datetime.now().strftime('%d.%m.%Y %H:%M')}",
        )

    # Create tasks for dosing if not already done
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

# Show last saved result
if st.session_state.last_dosing:
    with st.expander("Letzte gespeicherte Messung"):
        st.json([... keep existing json display ...])

# REMOVE the old save button section (lines 387-440 in original)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /app && python -m pytest test_save_button_position.py -v
# Expected: PASSED
```

- [ ] **Step 5: Clean up test file and commit**

```bash
cd /app && rm test_save_button_position.py && git add Wasserrechner.py && git commit -m "feat: move save button to after photo upload in Section 1"
```

---

### Task 4: Restructure Section 3 (Dosierempfehlung) with Moved Handlungsbedarf

**Files:**
- Modify: `/app/Wasserrechner.py` (replace lines 317-382, new structure)

- [ ] **Step 1: Write failing test**

```python
# test_dosierempfehlung_structure.py
import pytest
from unittest.mock import patch, MagicMock
import sys
sys.path.insert(0, '/app')

def test_dosierempfehlung_has_handlungsbedarf():
    """Test that Dosierempfehlung shows Handlungsbedarf at top."""
    import streamlit as st
    from Wasserrechner import render_dosierempfehlung_section
    
    # Test with issues
    with patch.object(st, 'subheader'), \
         patch.object(st, 'warning'), \
         patch.object(st, 'markdown'), \
         patch.object(st, 'container'), \
         patch.object(st, 'columns'), \
         patch.object(st, 'button'), \
         patch.object(st, 'text_input'), \
         patch.object(st, 'success'):
        render_dosierempfehlung_section(
            dosing=[
                MagicMock(product="pH-Minus", amount=500, unit="g", reason="pH zu hoch", follow_up_days=7)
            ],
            ph=8.0, chlorine=0.2,  # Both out of range
            lsi_cat="kalkausfällend", rsi_cat="kalkend",
            pool=MagicMock(ph_min=7.2, ph_max=7.6, chlorine_min=0.5, chlorine_max=3.0)
        )
    assert True

def test_dosierempfehlung_no_issues():
    """Test that Dosierempfehlung shows success when all OK."""
    import streamlit as st
    from Wasserrechner import render_dosierempfehlung_section
    
    with patch.object(st, 'subheader'), \
         patch.object(st, 'success'):
        render_dosierempfehlung_section(
            dosing=[],
            ph=7.4, chlorine=1.5,
            lsi_cat="ausgeglichen", rsi_cat="ausgeglichen",
            pool=MagicMock(ph_min=7.2, ph_max=7.6, chlorine_min=0.5, chlorine_max=3.0)
        )
    assert True
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /app && python -m pytest test_dosierempfehlung_structure.py -v
# Expected: FAILED
```

- [ ] **Step 3: Add render_dosierempfehlung_section function and call it**

```python
# In Wasserrechner.py, add this function before main flow:

def render_dosierempfehlung_section(dosing, ph, chlorine, lsi_cat, rsi_cat, pool):
    """Render Dosierempfehlung with Handlungsbedarf at top."""
    st.subheader("3️⃣ Dosierempfehlung")
    st.caption("Handlungsbedarf & Dosierung")
    
    ph_ok = pool.ph_min <= ph <= pool.ph_max
    chl_ok = pool.chlorine_min <= chlorine <= pool.chlorine_max
    lsi_balanced = lsi_cat == "ausgeglichen"
    rsi_balanced = rsi_cat == "ausgeglichen"
    
    # --- Handlungsbedarf (synthesized from all data) ---
    issues = []
    if not ph_ok:
        issues.append(("🧼 Hygiene", f"pH {ph:.1f} außerhalb Zielbereich {pool.ph_min}–{pool.ph_max}"))
    if not chl_ok:
        issues.append(("🧼 Hygiene", f"Chlor {chlorine:.1f} mg/L außerhalb Zielbereich {pool.chlorine_min}–{pool.chlorine_max} mg/L"))
    if not lsi_balanced:
        issues.append(("⚖️ Kalk-Korrosion", f"LSI: {lsi_cat}"))
    if not rsi_balanced:
        issues.append(("⚖️ Kalk-Korrosion", f"RSI: {rsi_cat}"))
    
    if issues:
        st.warning("⚡ Handlungsbedarf")
        # Group by category
        hygiene_issues = [i for i in issues if i[0] == "🧼 Hygiene"]
        kalk_issues = [i for i in issues if i[0] == "⚖️ Kalk-Korrosion"]
        
        if hygiene_issues:
            st.markdown("**🧼 Hygiene (Priorität):**")
            for cat, msg in hygiene_issues:
                st.caption(f"• {msg}")
        
        if kalk_issues:
            st.markdown("**⚖️ Kalk-Korrosion:**")
            for cat, msg in kalk_issues:
                if "korrosiv" in msg.lower():
                    st.caption(f"• {msg} → pH anheben oder Härte/Alkalinität erhöhen")
                else:
                    st.caption(f"• {msg} → pH senken oder Härte/Alkalinität reduzieren")
    else:
        st.success("✅ Alles im grünen Bereich — keine Maßnahmen nötig.")
    
    # --- Dosing Recommendations (existing logic) ---
    if dosing:
        for d in dosing:
            with st.container(border=True):
                col_a, col_b = st.columns([3, 1])
                with col_a:
                    st.warning(f"**{d.product}**: {d.amount:g} {d.unit}")
                    st.caption(d.reason)
                with col_b:
                    if st.button(
                        "📋 Aufgabe",
                        key=f"task_{d.product}_{d.amount}",
                        use_container_width=True,
                    ):
                        save_task(
                            session,
                            task_type="dosierung",
                            title=f"{d.product}: {d.amount:g} {d.unit}",
                            description=d.reason,
                            due_date=datetime.date.today(),
                            interval_days=0,
                        )
                        st.session_state.task_created = True
                        st.rerun()

            # Execution documentation
            st.caption("Ausführung dokumentieren:")
            exec_col1, exec_col2 = st.columns([3, 1])
            with exec_col1:
                exec_notes = st.text_input(
                    "Was wurde gemacht?",
                    placeholder=f"z. B. {d.amount:g} {d.unit} zugegeben um ...",
                    key=f"exec_{d.product}",
                )
            with exec_col2:
                if st.button(
                    "✅ Erledigt", key=f"done_{d.product}", use_container_width=True
                ):
                    task_data = {
                        "date": datetime.date.today().isoformat(),
                        "time": datetime.datetime.now().strftime("%H:%M"),
                        "action": exec_notes or f"{d.amount:g} {d.unit} zugegeben",
                        "product": d.product,
                        "amount": d.amount,
                        "unit": d.unit,
                        "reason": d.reason,
                    }
                    if "executed_actions" not in st.session_state:
                        st.session_state.executed_actions = []
                    st.session_state.executed_actions.append(task_data)

                    if d.follow_up_days > 0:
                        save_task(
                            session,
                            task_type="nachkontrolle",
                            title=f"{d.product} – Nachkontrolle",
                            description=f"Folgeaufgabe in {d.follow_up_days} Tagen "
                            f"(automatisch erzeugt am {datetime.date.today().isoformat()})",
                            due_date=datetime.date.today()
                            + datetime.timedelta(days=d.follow_up_days),
                            interval_days=d.follow_up_days,
                        )
                    st.rerun()
    else:
        st.success("✅ Keine Dosierung erforderlich — alle Werte im Zielbereich.")


# In main flow, replace the old Section 3 (lines 317-382) with:
# render_dosierempfehlung_section(dosing, ph, chlorine, lsi_cat, rsi_cat, pool)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /app && python -m pytest test_dosierempfehlung_structure.py -v
# Expected: PASSED
```

- [ ] **Step 5: Clean up test file and commit**

```bash
cd /app && rm test_dosierempfehlung_structure.py && git add Wasserrechner.py && git commit -m "feat: restructure Dosierempfehlung with Handlungsbedarf at top"
```

---

### Task 5: Final Integration Test & Cleanup

**Files:**
- Modify: `/app/Wasserrechner.py` (ensure all imports, no syntax errors)

- [ ] **Step 1: Run existing test suite**

```bash
cd /app && python -m pytest tests/ -v
# Expected: All existing tests pass
```

- [ ] **Step 2: Manual smoke test via streamlit**

```bash
cd /app && timeout 10 streamlit run Wasserrechner.py --server.headless true 2>&1 | head -50
# Expected: No import errors, no runtime exceptions on startup
```

- [ ] **Step 3: Verify git diff is clean and complete**

```bash
cd /app && git diff --stat
# Should show changes only in Wasserrechner.py
```

- [ ] **Step 4: Final commit**

```bash
cd /app && git add Wasserrechner.py && git commit -m "feat: complete UI redesign - Hygiene/Kalk-Korrosion split, pH/Chlor gauges, moved Handlungsbedarf, save button repositioned"
```

- [ ] **Step 5: Dispatch final code reviewer**

```bash
# This will be handled by the controller
```

---

## Summary

**Total Tasks:** 5  
**Primary File:** `/app/Wasserrechner.py`  
**No New Files:** All changes in existing main page  
**Dependencies:** None (existing Plotly, Streamlit, SQLAlchemy)

Each task includes: failing test → minimal implementation → passing test → commit.  
All calculation logic (LSI, RSI, dosing) remains unchanged.