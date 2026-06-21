# Handoff: Tracer — Structured Requirements Workbench

## Overview
Tracer is an AI-assisted PCB requirements workbench: an engineer describes a board in plain language, and Tracer extracts, organizes, and formalizes the requirements. This handoff covers the **Structured Requirements** screen — stage 3 of the workflow (Describe board → Intent analysis → **Structured requirements** → Formal specification). It presents the extracted requirements as editable cards grouped by engineering category, distinguishes user-**stated** from AI-**inferred** requirements, and renders a live JSON formal-spec export.

## About the Design Files
The file in this bundle (`Tracer Requirements.dc.html`) is a **design reference created in HTML** — a working prototype showing the intended look and behavior. It is **not** production code to copy directly. The task is to **recreate this design in the target codebase's existing environment** (React, Vue, etc.) using its established component library, state patterns, and styling approach. If no environment exists yet, choose the most appropriate framework and implement the design there.

Note: the prototype is authored as a "Design Component" (a streaming single-file format). The `class Component extends DCLogic` is conceptually a React class component minus `render()`; `renderVals()` returns the values/handlers consumed by the template. Treat it as pseudo-React — reimplement with your codebase's idioms (hooks, stores, etc.).

## Fidelity
**High-fidelity (hifi).** Final colors, typography, spacing, and interactions are specified. Recreate the UI pixel-accurately using the codebase's existing libraries and patterns. Exact hex values, font sizes, and spacing are listed in **Design Tokens**.

---

## Screens / Views

### Screen: Structured Requirements
**Purpose:** The engineer reviews AI-extracted PCB requirements, confirms or corrects them, edits values inline, filters by origin/category, and exports a formal JSON spec.

**Overall layout (top to bottom):**
1. **Header bar** — fixed, height `56px`, white, bottom border `1px #e4e0d8`.
2. **Stage tracker strip** — fixed, padding `11px 22px`, background `#faf8f3`, bottom border `1px #e4e0d8`.
3. **Main area** — fills remaining height. CSS Grid, 3 columns: `280px minmax(0,1fr) 360px`, `min-height:0; overflow:hidden`. Each column scrolls independently.

Root container: `height:100vh; display:flex; flex-direction:column; background:#f4f2ee; color:#1c1a16; font-family:'Inter'; overflow:hidden`.

#### Header bar components (left → right, `gap:18px`, padding `0 22px`)
- **Logo mark:** `23×23px`, radius `6px`, background `#1c1a16`, white "T" in IBM Plex Mono `13px/600`.
- **Wordmark:** "TRACER", IBM Plex Mono `13px`, weight `600`, letter-spacing `0.2em`.
- **Version chip:** "v0.4", IBM Plex Mono `10px`, color `#98917f`, border `1px #e4e0d8`, radius `5px`, padding `2px 6px`.
- **Vertical divider:** `1×24px`, `#e4e0d8`.
- **Project block:** label "PROJECT" (mono `9.5px`, letter-spacing `0.14em`, `#a39b8c`) + project name "rev-c-power-mux" (mono `13px/600`) + "REV C" chip (mono `9.5px`, `#7d7768`, bordered).
- **Status pill:** padding `4px 10px`, background `#fdf4e6`, border `1px #f0dcb5`, radius `20px`; contains a `6px` amber dot (`#c2620e`) + "analyzing" (mono `10.5px`, `#9a4d09`).
- **Spacer** (`flex:1`).
- **"Export JSON" button** (ghost): mono `11.5px`, `#46423a`, white bg, border `1px #ddd7cc`, radius `7px`, padding `8px 13px`. Hover: bg `#f7f4ef`, border `#cfc8bb`. Copies the JSON spec to clipboard; label changes to "Copied ✓" for ~1.6s.
- **"Formalize spec →" button** (primary): Inter `12.5px/600`, white text, bg `#c2620e`, border `1px #ad560c`, radius `7px`, padding `8px 15px`. Hover bg `#ad560c`. Advances the stage tracker to stage 4.

#### Stage tracker (4 stages, horizontal, `gap:18px`)
Each stage = circular dot + two-line label. Connector between stages is a `→` glyph (`#cfc9bd`, `14px`).
- **Dot:** `22×22px` circle, mono `11px/600`, centered.
  - *Done* (stage number < current): bg `#c2620e`, white "✓".
  - *Active* (= current): white bg, `#c2620e` text, `2px solid #c2620e` border, shows stage number.
  - *Pending* (> current): white bg, `#b3ab9c` text, `1px solid #d6d1c7` border, shows stage number.
- **Label lines:** top = "STAGE 0N" (mono `8.5px`, letter-spacing `0.14em`, `#b0a895`); bottom = stage name (`12.5px`; weight `600` if active else `500`; color `#1c1a16` if done/active else `#a39b8c`).
- Stages: `1 Describe board` (done), `2 Intent analysis` (done), `3 Structured requirements` (active, default), `4 Formal specification` (pending).

#### Left rail (`280px`, bg `#fbfaf6`, right border `1px #e4e0d8`, padding `18px 18px 30px`, scrolls)
1. **Plain-language brief**
   - Label row: "INPUT" badge (mono `10px`, `#9a4d09`, bg `#fbeed8`, border `1px #f0dcb5`, radius `4px`, padding `2px 6px`) + "plain language" (`11px`, `#a39b8c`).
   - Brief box: white, border `1px #e6e2da`, radius `8px`, padding `13px 14px`, mono `12px`, line-height `1.65`, `#46423a`. Copy:
     > Small USB-C powered mux board. 9–36 V input, needs 5 V at 3 A out. Talks I²C to a host controller. Must fit a 50 × 35 mm enclosure and run up to 70 °C ambient.
2. **Divider:** `1px #e9e5dd`, margin `20px 0`.
3. **Intent analysis** — section label "INTENT ANALYSIS" (mono `10px`, letter-spacing `0.12em`, `#8a8473`). Three label/value rows (`12.5px` `#6b665c` label; mono value):
   - "Requirements extracted" → `18` (`15px/600`, `#1c1a16`)
   - "Stated" → `6` (`14px/600`, `#3f7d57` green)
   - "Inferred" → `12` (`14px/600`, `#c2620e` amber)
   - **Overall confidence:** row "OVERALL CONFIDENCE" (mono `11px`, `#a39b8c`) + percentage (mono `12px/600`); below it a `6px` track (`#ece8e0`, radius `3px`) with amber (`#c2620e`) fill at the average confidence width (~`75%`).
4. **Divider.**
5. **Inferred assumptions** — label "INFERRED ASSUMPTIONS" + count `12`. List of 5 items, each = `6px` amber dot (`#c2620e`, top-aligned) + text (`12px`, `#46423a`, line-height `1.5`) + a mono reference tag (`10px`, `#b3ab9c`) like "→ PWR-03". Items:
   - "3.3 V logic rail assumed from I²C bus and MCU presence." → PWR-03
   - "Reverse-polarity FET added for wide 9–36 V input." → PWR-04
   - "USB 2.0 full-speed — no high-speed cue in the brief." → IF-01
   - "Enclosure fit implies 4 × M2.5 mounting holes." → MEC-02
   - "Edge-mounted USB-C for connector access through the case." → PLC-01

#### Center column (`minmax(0,1fr)`, padding `18px 22px 44px`, scrolls)
1. **Toolbar row** (`display:flex; justify-content:space-between; align-items:flex-end; flex-wrap:wrap; gap:12px 16px; margin-bottom:14px`):
   - Heading "Structured requirements" (`16px/600`, `#1c1a16`, letter-spacing `-0.01em`) + subtitle (mono `11px`, `#a39b8c`): "18 extracted · 6 stated · 12 inferred" (counts update live).
   - **Origin filter chips** (`gap:6px`): "All 18", "Stated 6", "Inferred 12". See Chip spec below.
2. **Category chip row** (`flex-wrap:wrap; gap:6px; margin-bottom:20px`): "All 18", "Power 5", "Interfaces 3", "Components 2", "Signal Integrity 2", "Thermal 2", "Mechanical 2", "Placement 2".
3. **Requirement groups** — one section per category (when sorted by category). Section header: category name (mono `11px`, letter-spacing `0.13em`, uppercase, `#8a8473`) + count (mono `10px`, `#b3ab9c`) + a `flex:1` hairline (`1px #e9e5dd`). Cards stacked with `gap:8px`.

**Chip spec** (both filter + category): mono `11px/500`, letter-spacing `0.03em`, padding `5px 11px`, radius `7px`, `cursor:pointer`, `white-space:nowrap`.
- *Active:* bg `#1c1a16`, white text, border `1px #1c1a16`.
- *Inactive:* white bg, `#5a5448` text, border `1px #e0dbd1`.

**Requirement card** (`display:flex; gap:13px`, white bg, border `1px #e6e2da`, radius `8px`, padding `13px 15px`; hover border `#d4cdbf`):
- **Origin strip** (left): `3px` wide, full height (`align-self:stretch`), radius `3px`. Color: amber `#c2620e` if inferred-and-highlighted; `#d3ccbf` inferred-unhighlighted; `#9bbf9f` (green) if stated.
- **Body** (`flex:1; min-width:0`):
  - Top row (`align-items:center; gap:9px`): requirement ID (mono `11px/500`, `#8a8473`); **origin badge button**; spacer; **confidence block** (optional).
  - **Origin badge** (clickable button): mono `9.5px/500`, letter-spacing `0.08em`, padding `3px 7px`, radius `4px`. *Stated:* `#3f6b50` text, bg `#e7efe7`, border `1px #cfe0d2`, label "STATED". *Inferred (highlighted):* `#9a4d09` text, bg `#fbeed8`, border `1px #f0dcb5`, label "INFERRED". *Inferred (not highlighted):* `#6b665c` text, bg `#efece6`, border `1px #e0dbd1`. Clicking toggles stated↔inferred.
  - **Confidence block** (`gap:7px`): "CONF" (mono `9.5px`, `#b0a895`) + a `56×5px` track (`#ece8e0`, radius `3px`) with fill + percentage (mono `11px`, `#6b665c`, right-aligned, width `30px`). Fill color by confidence: `≥0.85` → `#3f7d57`; `≥0.70` → `#c2620e`; else `#cf9134`.
  - **Title** (`13px`, `#5a5448`, margin `7px 0 1px`).
  - **Value** (inline editable `<input>`): full width, no border except a bottom border; mono `13.5px/500`, `#1c1a16`, padding `3px 0`, transparent bg. Bottom border transparent by default → `#e0dbd1` on hover → `#c2620e` on focus. Editing updates the value in state and the JSON live.

#### Right rail (`360px`, bg `#fbfaf6`, left border `1px #e4e0d8`, `display:flex; flex-direction:column`)
1. **Header row** (padding `16px 16px 12px`): "FORMAL SPECIFICATION" (mono `10px`, letter-spacing `0.12em`, `#8a8473`) + spacer + "JSON" tab chip (mono `10.5px`, `#1c1a16`, white bg, border `1px #ddd7cc`, radius `5px`, padding `3px 9px`).
2. **Code panel** (`flex:1`, margin `0 16px`, bg `#1b1916`, radius `9px`, column, `overflow:hidden`):
   - Panel header (padding `9px 12px`, bottom border `1px #2c2924`): `9px` amber dot + filename "rev-c-power-mux.req.json" (mono `10.5px`, `#8c857a`) + spacer + **copy button** (mono `10.5px`, `#c9c2b5`, bg `#2a2722`, border `1px #3a362f`, radius `5px`, padding `4px 9px`; hover bg `#34302a`; label "copy" → "copied ✓").
   - `<pre>`: `flex:1; overflow:auto`, padding `13px 15px`, mono `11.5px`, line-height `1.6`, color `#cfc8b9`, `white-space:pre`. Contents = the live JSON spec.
3. **Footer** (padding `13px 16px 16px`, `align-items:center; gap:9px`): `6px` amber dot + note (`11px`, `#8a8473`): "Regenerated live from current requirements" (becomes "Specification formalized · ready for export" once Formalize is clicked).

---

## Interactions & Behavior
- **Edit value:** typing in any card's value input updates that requirement's `value` in state; the JSON spec re-renders immediately.
- **Toggle origin:** clicking a card's origin badge flips `stated ↔ inferred`. Confidence adjusts: promoting to stated → `min(0.99, conf + 0.2)`; demoting to inferred → `max(0.5, conf − 0.2)`. Strip color, badge style, confidence bar, sidebar counts, subtitle, and JSON all update.
- **Origin filter:** All / Stated / Inferred — filters which cards show. Active chip = dark.
- **Category filter:** All / per-category — filters by category. Active chip = dark.
- **Copy / Export JSON:** both the header "Export JSON" button and the code-panel "copy" button write the JSON string to the clipboard (`navigator.clipboard.writeText`) and show a transient confirmation (~1600ms).
- **Formalize:** sets the stage to 4 (Formal specification becomes active, Structured requirements becomes done) and updates the right-rail footer note.
- **Responsive:** desktop app screen. Grid center uses `minmax(0,1fr)` to avoid overflow; the center toolbar wraps the filter chips below the heading at narrow widths. Each of the three columns scrolls independently; the page itself does not scroll (`100vh`, `overflow:hidden`).

## State Management
State variables:
- `filter`: `'all' | 'stated' | 'inferred'` (default `'all'`).
- `category`: `'all' | 'power' | 'interfaces' | 'components' | 'signal' | 'thermal' | 'mechanical' | 'placement'` (default `'all'`).
- `stage`: number, current active stage 1–4 (default `3`).
- `copied`: boolean, transient clipboard-confirmation flag (auto-resets after 1600ms).
- `requirements`: array of requirement objects (the source of truth). Each:
  ```
  { id: string, cat: string, title: string, value: string, kind: 'stated'|'inferred', conf: number(0–1) }
  ```

Derived (computed from state on each render):
- `total`, `statedCount`, `inferredCount`, average confidence / `overallPct`.
- `groups`: requirements grouped by category (or a single sorted group when `sortMode` ≠ `category`), each decorated with display styles (strip color, badge style, bar width/color, percentage label).
- `filters` / `cats`: chip definitions with active styling and counts.
- `stages`: tracker definitions with done/active/pending styling.
- `jsonText`: `JSON.stringify` of the spec object (see Assets/Data below).

No data fetching in the prototype — `requirements` is seeded inline. In production this would come from the intent-analysis backend.

### Configurable options (exposed as tweaks; treat as props/settings)
- `showConfidence` (boolean, default `true`) — show/hide the per-card confidence block.
- `highlightInferred` (boolean, default `true`) — when off, inferred cards use neutral grey strip/badge instead of amber.
- `sortMode` (`'category' | 'confidence' | 'origin'`, default `'category'`) — `category` groups by engineering category; `confidence` shows one group sorted by confidence desc; `origin` shows one group with inferred first.

## Design Tokens
**Colors**
| Role | Hex |
|---|---|
| Page background | `#f4f2ee` |
| Panel / card background | `#ffffff` |
| Rail background | `#fbfaf6` |
| Stage strip background | `#faf8f3` |
| Primary text | `#1c1a16` |
| Secondary text | `#46423a` / `#5a5448` |
| Tertiary / muted text | `#6b665c`, `#8a8473`, `#a39b8c`, `#b0a895`, `#b3ab9c` |
| Hairline border | `#e4e0d8`, `#e6e2da`, `#e9e5dd` |
| Stronger border | `#d6d1c7`, `#ddd7cc`, `#e0dbd1` |
| **Accent (amber)** | `#c2620e` |
| Accent hover / dark | `#ad560c` |
| Amber tint bg | `#fdf4e6`, `#fbeed8` / border `#f0dcb5` |
| Amber text | `#9a4d09` |
| Stated green (text) | `#3f6b50` / `#3f7d57` |
| Stated green tint bg | `#e7efe7` / border `#cfe0d2`; strip `#9bbf9f` |
| Confidence mid (amber) | `#c2620e`; low | `#cf9134` |
| Neutral inferred (unhighlighted) strip | `#d3ccbf`; badge bg `#efece6` |
| Track / bar background | `#ece8e0` |
| Code panel bg | `#1b1916`; header border `#2c2924`; button bg `#2a2722`, border `#3a362f`; text `#cfc8b9` / `#8c857a` / `#c9c2b5` |
| Selection highlight | `#f3d7af` |

**Typography**
- Body / UI: **Inter** (400, 500, 600).
- Mono (IDs, values, code, metadata, labels): **IBM Plex Mono** (400, 500, 600).
- Sizes used: `8.5, 9.5, 10, 10.5, 11, 11.5, 12, 12.5, 13, 13.5, 14, 15, 16` px. Letter-spacing for mono labels: `0.03–0.2em`.

**Radii:** `4px` (badges), `5px` (small chips/buttons), `6px` (logo, dots track), `7px` (chips/buttons), `8px` (cards/brief), `9px` (code panel), `20px` (status pill), `50%` (dots).

**Spacing:** column gaps `13–18px`; card padding `13px 15px`; rail padding `18px`; section dividers margin `20px 0`. No drop shadows used — depth comes from hairline borders and the dark code panel.

**Borders:** `1px` solid hairlines throughout; `2px` only on the active stage dot; `3px` origin strip.

## Assets
- **Fonts:** Inter + IBM Plex Mono via Google Fonts (`https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=Inter:wght@400;500;600&display=swap`). Substitute with your codebase's equivalents if it self-hosts fonts.
- **No images or icon assets.** All glyphs are Unicode (`✓`, `→`) or pure-CSS shapes (dots, strips, bars). No SVG icon set required.

### Sample data / JSON export shape
Exported spec object (pretty-printed):
```json
{
  "project": "rev-c-power-mux",
  "revision": "C",
  "generated": "2026-06-20",
  "summary": { "total": 18, "stated": 6, "inferred": 12, "confidence": 0.75 },
  "requirements": {
    "power": [
      { "id": "PWR-01", "title": "Input voltage range", "value": "9 – 36 V DC", "origin": "stated", "confidence": 0.98 }
    ]
  }
}
```
Full seed list (id · category · title · value · origin · confidence):
- PWR-01 · power · Input voltage range · "9 – 36 V DC" · stated · 0.98
- PWR-02 · power · Primary output rail · "5.0 V @ 3.0 A" · stated · 0.97
- PWR-03 · power · Logic rail · "3.3 V @ 1.5 A" · inferred · 0.74
- PWR-04 · power · Reverse-polarity protection · "Required · P-FET" · inferred · 0.69
- PWR-05 · power · Quiescent current · "< 50 µA" · inferred · 0.58
- IF-01 · interfaces · Host link · "USB-C · USB 2.0 FS" · stated · 0.95
- IF-02 · interfaces · Control bus · "I²C @ 400 kHz" · stated · 0.96
- IF-03 · interfaces · Debug port · "SWD · 10-pin 1.27 mm" · inferred · 0.71
- CMP-01 · components · Buck converter · "Sync · ≥ 90% eff" · inferred · 0.66
- CMP-02 · components · Microcontroller · "Cortex-M0+ class" · inferred · 0.62
- SI-01 · signal · USB differential impedance · "90 Ω ± 10%" · inferred · 0.78
- SI-02 · signal · I²C pull-ups · "2.2 kΩ to 3V3" · inferred · 0.64
- TH-01 · thermal · Max ambient · "70 °C" · stated · 0.94
- TH-02 · thermal · Junction margin · "≥ 20 °C" · inferred · 0.60
- MEC-01 · mechanical · Board outline · "50 × 35 mm" · stated · 0.99
- MEC-02 · mechanical · Mounting · "4 × M2.5" · inferred · 0.67
- PLC-01 · placement · USB-C connector · "Board edge · south" · inferred · 0.63
- PLC-02 · placement · Connectors · "Top side only" · inferred · 0.61

Category labels: power→Power, interfaces→Interfaces, components→Components, signal→Signal Integrity, thermal→Thermal, mechanical→Mechanical, placement→Placement.

## Screenshots
In `screenshots/`:
- `01-overview.png` — default Structured Requirements view (all requirements, grouped by category).
- `02-inferred-filter.png` — origin filter set to "Inferred".
- `03-power-category.png` — category filter set to "Power".

## Files
- `Tracer Requirements.dc.html` — the hifi design reference (template markup + logic class). Open in a browser to interact with the live prototype.
- `support.js` — runtime needed for the `.dc.html` to render locally.
- `screenshots/` — reference captures of the design.
