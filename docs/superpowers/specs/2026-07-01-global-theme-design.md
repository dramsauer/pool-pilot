# Global Theme (Teal Blue + Merriweather)

Custom Streamlit theme for PoolPilot with a teal-blue primary (`#007982`), warm yellow accents, and Merriweather serif font for a clean scientific look.

## Color Palette

| Role | Hex |
|---|---|
| Primary / accent | `#007982` |
| Primary hover | `#006269` |
| Background | `#FFFFFF` |
| Secondary background | `#F0F5F6` |
| Text | `#1A2B2C` |
| Warning / highlight | `#E8A838` |
| Success | `#2E9E6D` |

## Font

- **Merriweather** from Google Fonts for body text
- Fallback: `Georgia, serif`
- Headings: Merriweather Bold

## Implementation

### `.streamlit/config.toml` (native theme)
```toml
[theme]
primaryColor = "#007982"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F0F5F6"
textColor = "#1A2B2C"
font = "serif"
```

### `utils/theme.py` (CSS injection)
- Load Merriweather via `@import url(...)`
- Apply `font-family` globally
- Style tweaks for headings, borders, badges
- Yellow accent for warnings

### Pages to update
Each page calls `inject_theme()` after `st.set_page_config(...)`.

## Files Changed

| File | Change |
|---|---|
| `.streamlit/config.toml` | **NEW** — native theme config |
| `utils/theme.py` | **NEW** — `inject_theme()` function |
| `Wasserrechner.py` | **MODIFY** — call `inject_theme()` |
| `pages/01_Poolverwaltung.py` | **MODIFY** — call `inject_theme()` |
| `pages/02_Verlauf.py` | **MODIFY** — call `inject_theme()` |
| `pages/03_Wartung.py` | **MODIFY** — call `inject_theme()` |
| `pages/04_Kalender.py` | **MODIFY** — call `inject_theme()` |
| `pages/09_Datenverwaltung.py` | **MODIFY** — call `inject_theme()` |
