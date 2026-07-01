# Data Export / Import

Export all data as `.zip` (pool.db + photos) and import from a backup ZIP with per-category merge options.

## Motivation

- Backup / data safety
- Migration between instances (local ↔ Docker)
- Recovery after data loss
- Partial merging of datasets from different sources

## Location & Navigation

- **New page:** `pages/09_Datenverwaltung.py`
- **Navigation:** In `Wasserrechner.py` sidebar: `st.sidebar.expander("Weitere")` → `st.page_link("pages/09_Datenverwaltung.py", label="🔐 Daten-Export/-Import")`
- Streamlit's auto-nav also lists the page at the bottom (high number = less prominent)

## Export

Creates a ZIP archive of the entire `data/` directory.

**Implementation:**
- `zipfile.ZipFile` writes `pool.db` + all files from `photos/` into `io.BytesIO`
- `st.download_button(data=bytes_io.getvalue(), file_name=..., mime="application/zip")`
- Filename: `poolpilot-backup-YYYY-MM-DD.zip`

**UI:**
```
┌─ Export ───────────────────────────────┐
│                                         │
│  📦 [ Download full backup (ZIP) ]     │
│    pool.db + all photos                 │
│                                         │
└─────────────────────────────────────────┘
```

## Import

### User Flow

1. **ZIP upload** — `st.file_uploader` accepts `.zip`
2. **Analysis** — ZIP is inspected:
   - Does `pool.db` exist? (validation)
   - If not: error, no import possible
   - If yes: open imported DB (separate SQLAlchemy engine, read-only), get record counts per table
   - Compare with current DB (counts per category)
3. **Category selection** — Per category, user chooses:
   - **Replace** — delete current records, insert imported ones
   - **Merge** — match by key, skip duplicates, add new ones
   - **Skip** — ignore this category
4. **Execute** — Confirmation dialog → merge execution
5. **Result** — Summary per category

### Categories & Merge Keys

| Category | Description | Merge Key |
|---|---|---|
| Pools | Pool configurations | `name` |
| Products | Chemicals | `name` |
| Instruments | Measurement devices | `name` |
| Tap Water Sources | Drinking water analyses | `name` |
| Task Templates | Recurring task templates | `title` |
| Measurements | Readings + associated Photos | `timestamp` + `pool_id` |
| Tasks | MaintenanceTasks | `title` + `due_date` |

### Merge Modes

**Replace:**
- Delete all current records of the category (CASCADE via ORM)
- Insert all imported records → new IDs

**Merge:**
- For each imported record: lookup by merge key in current DB
- Found → keep existing, record ID mapping
- Not found → insert new, record ID mapping

**Skip:**
- No changes to this category
- No ID mapping built → dependent categories can't import

### Dependency Order & ID Remapping

Execution follows FK dependency order. An ID mapping is built per category: `id_map[category][imported_id] = current_id`.

```
1. Instruments        (no FK dependencies)
2. Tap Water Sources  (no FK dependencies)
3. Products           (no FK dependencies)
4. Task Templates     (no FK dependencies)
5. Pools              (no FK dependencies)
   ↓
6. PoolTaskDefaults   (FK: pools, task_templates) — automatic
   ↓
7. Readings           (FK: pools → id_map["pools"])
   ↓
8. Photos             (FK: readings → id_map["readings"] + copy files)
   ↓
9. MaintenanceTasks   (FK: pools, readings, products → id_map)
```

**Warning:** If a parent category is set to "Skip" and a child category is not, a warning is shown before execution.

### Photos

- **Replace:** Delete old files in `data/photos/` + DB records → copy imported files + insert DB records
- **Merge:** Match by `reading_id` + filename, add new ones
- **Skip:** No changes

### Transaction Behavior

Each category runs in its own transaction — if one category fails, only that category is rolled back, others continue. The user sees a detailed result summary.

## UI Layout

```
╔══════════════════════════════════════════════════╗
║  Data Export / Import                            ║
║                                                  ║
║  ─── Export ─────────────────────────────────    ║
║  [Download full backup]                          ║
║                                                  ║
║  ─── Import ─────────────────────────────────    ║
║  [⬆ Upload ZIP]  [Analyze]                      ║
║                                                  ║
║  ZIP contents: 3 pools, 15 products, 0 photos   ║
║                                                  ║
║  Category           Current  Import  Action       ║
║  ─────────────────  ───────  ──────  ───────     ║
║  Pools                   2       3  [Merge ▼]    ║
║  Products               10       8  [Replace ▼]  ║
║  ...                                            ║
║                                                  ║
║  ⚠ Warning: "Measurements" requires "Pools"     ║
║                                                  ║
║  [🚀 Run Import]                                 ║
║                                                  ║
║  ─── Result ──────────────────────────           ║
║  ✅ Pools: 1 new, 2 kept                         ║
║  ✅ Products: 8 replaced                         ║
║  ...                                             ║
╚══════════════════════════════════════════════════╝
```

## Files Changed

| File | Change |
|---|---|
| `pages/09_Datenverwaltung.py` | **NEW** — Streamlit UI for export/import |
| `utils/export_import.py` | **NEW** — Core logic (ZIP, analysis, merge) |
| `Wasserrechner.py` | **MODIFY** — Add sidebar link under "Weitere" |
| `tests/test_export_import.py` | **NEW** — Tests |

## Tests

- Export produces valid ZIP with correct contents
- Import of an export → roundtrip (data identical)
- Merge modes: Replace / Merge / Skip
- ID remapping with FK dependencies
- Error cases: corrupt ZIP, missing `pool.db`, empty DB
- Partial import (one category fails, others continue)

## Error Handling & Edge Cases

- **Invalid ZIP:** Error message, no import
- **Schema version mismatch:** Warning (check via `_db_version` or table structure)
- **Photo file conflicts:** Auto-append suffix on name collision
- **Large uploads:** No hard limit (respect Streamlit's built-in limits)
- **DB connection error:** Rollback per category, clear error message
