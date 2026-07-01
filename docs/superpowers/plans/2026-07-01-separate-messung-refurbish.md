# Separate Messung — Refurbish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce vertical space of the water level slider to 180px and integrate the visual height bar immediately adjacent to the slider, removing the gap.

**Architecture:** Single-file change to `Wasserrechner.py`. The `streamlit_vertical_slider` iframe and the visual bar are placed side-by-side in `st.columns` with zero gap. CSS `flex: 0 0 auto` on the inner columns shrinks them to content width.

**Tech Stack:** Python, Streamlit, `streamlit_vertical_slider`

---

### Task 1: Refurbish water level section

**Files:**
- Modify: `Wasserrechner.py:236-288`

- [ ] **Step 1: Replace the inner columns + bar with compact layout**

  Replace the inner `vs_col, bar_col = st.columns([3, 1])` block and all its content with a zero-gap column layout plus a compact bar at 180px.

  Old code (lines 242–276):
  ```python
          st.markdown(
              "<style>div[data-testid='columns']:has(> div[data-testid='column'] div.st-key-water_vertical){gap:0!important}</style>",
              unsafe_allow_html=True,
          )
          vs_col, bar_col = st.columns([3, 1])
          with vs_col:
              water_level_cm = vertical_slider(
                  label="Wasserstand (cm)",
                  min_value=lo, max_value=hi,
                  default_value=int(pool.min_fill_height_cm),
                  step=1,
                  height=280,
                  track_color="lightgray",
                  slider_color="mediumseagreen",
                  thumb_color="mediumseagreen",
                  value_always_visible=True,
                  key="water_vertical",
              )
          with bar_col:
              pct = lambda v: v / hi * 100
              st.markdown(f"""
  <div style="margin:28px 0 0">
      <div style="display:flex;align-items:stretch;height:280px">
          <div style="position:relative;width:24px;flex-shrink:0;background:#e0e0e0;border-radius:8px">
              <div style="position:absolute;bottom:{pct(min_cm):.1f}%;width:100%;height:{pct(max_cm-min_cm):.1f}%;background:#81c784;border-radius:6px"></div>
              <div style="position:absolute;bottom:{pct(water_level_cm):.1f}%;width:100%;height:4px;background:#1a1a1a;border-radius:2px"></div>
          </div>
          <div style="position:relative;flex:1;font-size:13px;line-height:1.3;color:#333;font-weight:500;margin-left:6px">
              <span style="position:absolute;top:0">▲ {hi}</span>
              <span style="position:absolute;top:{100-pct(max_cm):.1f}%;transform:translateY(-50%)">Max {max_cm:.0f}</span>
              <span style="position:absolute;top:{100-pct(min_cm):.1f}%;transform:translateY(-50%)">Min {min_cm:.0f}</span>
              <span style="position:absolute;bottom:0">▼ 0</span>
          </div>
      </div>
  </div>""", unsafe_allow_html=True)
  ```

  New code:
  ```python
          st.markdown("""
  <style>
  div[data-testid='columns']:has(> div[data-testid='column'] div.st-key-water_vertical) {
      gap: 4px !important;
  }
  div[data-testid='columns']:has(> div[data-testid='column'] div.st-key-water_vertical) > div[data-testid='column'] {
      flex: 0 0 auto !important;
      padding-right: 0 !important;
  }
  </style>
  """, unsafe_allow_html=True)
          inner_cols = st.columns(2)
          with inner_cols[0]:
              water_level_cm = vertical_slider(
                  label="Wasserstand (cm)",
                  min_value=lo, max_value=hi,
                  default_value=int(pool.min_fill_height_cm),
                  step=1,
                  height=180,
                  track_color="lightgray",
                  slider_color="mediumseagreen",
                  thumb_color="mediumseagreen",
                  value_always_visible=True,
                  key="water_vertical",
              )
          with inner_cols[1]:
              pct = lambda v: v / hi * 100
              st.markdown(f"""
  <div style="display:flex;gap:4px;align-items:stretch;height:180px;padding-top:28px">
      <div style="position:relative;width:18px;flex-shrink:0;background:#e0e0e0;border-radius:6px">
          <div style="position:absolute;bottom:{pct(min_cm):.1f}%;width:100%;height:{pct(max_cm-min_cm):.1f}%;background:#81c784;border-radius:4px"></div>
          <div style="position:absolute;bottom:{pct(water_level_cm):.1f}%;width:100%;height:3px;background:#1a1a1a;border-radius:2px"></div>
      </div>
      <div style="position:relative;font-size:11px;line-height:1.3;color:#333;font-weight:500;white-space:nowrap">
          <span style="position:absolute;top:0;font-weight:600">▲ {hi}</span>
          <span style="position:absolute;top:{100-pct(max_cm):.1f}%;transform:translateY(-50%)">Max {max_cm:.0f}</span>
          <span style="position:absolute;top:{100-pct(min_cm):.1f}%;transform:translateY(-50%)">Min {min_cm:.0f}</span>
          <span style="position:absolute;bottom:0;font-weight:600">▼ 0</span>
      </div>
  </div>
  """, unsafe_allow_html=True)
  ```

- [ ] **Step 2: Verify it renders**

  Run the app and check that the water level slider renders at 180px with the visual bar immediately to its right.

  Run: `streamlit run Wasserrechner.py`
  Expected: The "Separate Messung" section shows the water level slider at 180px with the green-zone bar and labels right next to it, no large gaps. Temperature slider remains unchanged at 280px.

- [ ] **Step 3: Commit**

  ```bash
  git add Wasserrechner.py
  git commit -m "refurbish: compact Separate Messung water level to 180px with adjacent bar"
  ```
