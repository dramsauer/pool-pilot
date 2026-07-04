# Kalender-Seite — streamlit-calendar Implementierungsplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ersetze die handgebaute HTML-Kalendergrid + Monatsnavigation in `04_Kalender.py` durch `streamlit-calendar`.

**Architecture:** Minimaler Eingriff — eine `streamlit_calendar`-Komponente ersetzt ~80 Zeilen Custom-HTML/JS. Retro-Formular und Aufgabenliste bleiben unberührt.

**Tech Stack:** Streamlit, streamlit-calendar (FullCalendar-Wrapper)

---

### Task 1: Dependency hinzufügen

**Files:**
- Modify: `pyproject.toml:16`

- [ ] **Step 1: streamlit-calendar zu dependencies hinzufügen**

```toml
dependencies = [
    "streamlit>=1.50",
    "sqlalchemy>=2.0",
    "plotly>=5.20",
    "pillow>=10.0",
    "pandas>=2.1",
    "streamlit-calendar>=1.0",
]
```

- [ ] **Step 2: Paket installieren**

Run: `pip install streamlit-calendar`

Expected: Installation ohne Fehler.

---

### Task 2: Kalender-Grid ersetzen

**Files:**
- Modify: `pages/04_Kalender.py`

- [ ] **Step 1: Import anpassen**

Entferne `import calendar` und ersetze durch `from streamlit_calendar import calendar as st_calendar`.

Result:
```python
import datetime
import streamlit as st
from streamlit_calendar import calendar as st_calendar
from database.db import get_engine, init_db, get_session
from database.models import MaintenanceTask
from utils.theme import inject_theme
from utils.nav import render_sidebar
from database.repository import (
    get_pools, get_tasks_by_date_range,
    complete_task_with_notes,
    ensure_template_instances,
)
```

- [ ] **Step 2: Monatsnavigation (Buttons + session_state) entfernen**

Entferne die Blöcke:
- `if "cal_year" not in st.session_state: ...`
- `if "cal_month" not in st.session_state: ...`
- `nav = st.columns([1, 3, 1]) ...` (3 Buttons + reruns)

- [ ] **Step 3: Kalenderdaten-Beschaffung anpassen**

Ersetze `first_day`/`last_day` Berechnung (nutzte `calendar.monthrange` + session_state) durch festen aktuellen Monat:

```python
today = datetime.date.today()
first_day = today.replace(day=1)
if today.month == 12:
    last_day = today.replace(day=31)
else:
    last_day = (today.replace(day=1) + datetime.timedelta(days=32)).replace(day=1) - datetime.timedelta(days=1)
```

- [ ] **Step 4: Tasks zu FullCalendar-Events konvertieren**

Ersetze das `tasks_by_date`-Dictionary und die HTML-Grid-Erzeugung durch:

```python
events = []
for t in tasks:
    if t.completed:
        color = "#2e7d32"
    elif t.template_id:
        color = "#1565c0"
    elif t.follow_up_days and t.follow_up_days > 0:
        color = "#e65100"
    else:
        color = "#c62828"
    events.append({
        "title": t.title,
        "start": str(t.due_date),
        "end": str(t.due_date),
        "color": color,
        "allDay": True,
    })
```

- [ ] **Step 5: HTML-Grid + st.components.v1.html entfernen, streamlit-calendar einfügen**

Entferne:
```python
html = """
<style>
.cal-grid { ... }
...
</style>
<div class="cal-grid"> ... </div>
"""
st.components.v1.html(html, height=600, scrolling=True)
```

Ersetze durch:
```python
cal_options = {
    "initialView": "dayGridMonth",
    "headerToolbar": {
        "left": "prev,next today",
        "center": "title",
        "right": "",
    },
    "height": 600,
    "dayMaxEvents": 3,
}

st_calendar(events=events, options=cal_options, key="pool_calendar")
```

- [ ] **Step 6: Unused-Code aufräumen**

Entferne die Zeilen die nicht mehr gebraucht werden:
- `import calendar` → gelöscht
- `tasks_by_date`-Dictionary und Loop → gelöscht (gehört zur Grid)
- `now = datetime.date.today()` → nur noch im Retro-Formular nötig, als lokale Variable dort belassen

- [ ] **Step 7: Manuell testen**

Run: `streamlit run Wasserrechner.py`

Expected:
- Kalender-Seite zeigt streamlit-calendar mit Aufgaben als farbige Events
- Monatsnavigation (prev/next/today) funktioniert
- Retro-Formular funktioniert
- Aufgabenliste unterhalb funktioniert (Erledigen, Notizen, Dosis)
