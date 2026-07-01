# Separate Messung — Refurbish

## Motivation

Die "Separate Messung"-Section nimmt zu viel vertikalen Platz ein (280 px pro
Slider).  Die visuelle Höhenleiste steht neben dem Füllstand-Slider — zu weit
weg, um die Min/Max-Zone gut mit dem Sliderwert abzugleichen.

## Design-Entscheidungen

- **Nur Wasserstand-Slider** wird umgebaut (Temperatur bleibt unverändert, da
  dort keine visuelle Leiste existiert).
- **Option A (compact side-by-side):** Slider + Höhenleiste + Labels in einer
  flex-Gruppe, direkt aneinander angrenzend.  Die Leiste kann nicht als
  Slider-Hintergrund realisiert werden, weil `streamlit_vertical_slider` in
  einem Iframe rendert.
- **Höhe:** 180 px (von 280 px reduziert).

## Layout

```
col_water
└── .water-level-wrapper (flex, align-items: stretch)
    ├── vertical_slider (height=180, key="water_vertical")
    └── .bar-group (flex, gap: 4px)
        ├── .green-zone-bar (18 px breit)
        │   ├── green zone (min → max, opacity 0.4)
        │   └── black level line (3 px)
        └── .labels (11 px, position:absolute nach %
            Min/Max/Hi/0)
```

Der Slider wird in einer `st.columns([...])`-Group mit `gap="small"`
platziert, die Leiste in der nächsten Spalte.  Per CSS wird der default-Abstand
der Spalten entfernt (`gap: 2px !important`).

Die grüne Zone und die Level-Linie werden prozentual zur Gesamthöhe (`hi`)
positioniert, identisch zur aktuellen Implementierung.

## Beibehalt

- Volumen-Anzeige unterhalb (Caption)
- Temperatur-Slider unverändert (280 px, 2. Spalte)
- Alle Funktionslogik (CSI/LSI/RSI Referenzen)
- "Wasserstand: Min/Max in Pool-Einstellungen hinterlegen"-Fallback

## Dateien

| Datei | Änderung |
|---|---|
| `Wasserrechner.py` | Section 236–288: Layout umbauen, Height auf 180, Spalten-Gap entfernen |

Keine neuen Dateien, kein CSS-Framework.
