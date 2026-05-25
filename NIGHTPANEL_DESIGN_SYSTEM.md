# nightpanel design system

Design rules for dailydriver's nightpanel theme. This is the authoritative reference — any new UI surface must conform to these rules before shipping.

---

## philosophy

Inspired by Saab night-panel instrument clusters: pure black background, monochrome instrument-green text, a single amber register for secondary information, and one bright-green accent reserved for confirmed/active state. No white. No rounded colorful chips. No gradients. No bold weight.

The goal is an instrument panel, not a settings app.

---

## color vocabulary

All colors are defined as CSS custom properties in `theme_service.py → _build_theme_css()`. They scale with the brightness slider (range 0.3–1.5).

| token | base hex | role |
|---|---|---|
| `@text_primary` | `#7DB890` | instrument scale green — what things ARE (titles, items, section headers) |
| `@text_secondary` | `#B08030` | amber — context, descriptions, subtitles, secondary info |
| `@text_active` | `#26DE81` | bright green — ON state, confirmed, active toggles |
| `@text_dim` | `#2E5040` | very quiet — ghost labels, badge counts, disabled items |
| `@accent_color` | `#26DE81` (green) | active toggles, checkmarks, slider fill — only for confirmed state |
| `@accent_bg_color` | `#0A5C35` | background behind accent elements (switch checked, etc.) |
| `@window_bg_color` | `#0A0A0A` | main window background |
| `@card_bg_color` | `#111111` | card and list surfaces |
| `@sidebar_bg_color` | `#050505` | nav sidebar — slightly darker than main |
| `@headerbar_bg_color` | `#000000` | pure black header bar |
| `@border_quiet` | `#2A2A2A` | subtle separators, inactive row borders |
| `@border_default` | `#383838` | standard borders |
| `@border_selected` | `#5A5A5A` | selected-row border — grey, NOT accent |

Additional accents (amber, cyan, red, white) are available in `ACCENTS` dict but the default is green. The accent is only used for active/confirmed state; it is never used for text color on regular items.

---

## typography

- **font**: Inter (regular), JetBrains Mono for key labels and code
- **weight**: 400 everywhere — no bold, ever
- **case**: all lowercase everywhere — no Title Case, no ALLCAPS in content (the tab bar uses `.upper()` deliberately as a design element, not content)
- **size**: base size throughout; exceptions are section labels (0.70em) and captions (0.72em)

---

## color assignment rules

### green (`@text_primary`)
Everything that IS something — names, titles, actions, section headers, labels.

- row titles (`.boxed-list row label.title`, `row label.title`)
- preferences group titles (`preferencesgroup > box > label.title`)
- category/group section headers (`.sidebar-section-label`, `label.heading`, `label.title-2`, `label.title-3`)
- sidebar nav items (`.navigation-sidebar listboxrow label`)
- expander titles (`expander-widget title label`)
- checkbutton labels
- key badges (`shortcutlabel`, `keycap`)
- header bar title
- combo row text
- cheat sheet card headings

### amber (`@text_secondary`)
Everything that DESCRIBES something — supporting text, hints, secondary info.

- row subtitles (`row label.subtitle`)
- preferences group descriptions (`preferencesgroup > box > label.subtitle`)
- dim-labels (`label.dim-label`)
- captions (`label.caption`)
- card secondary labels (`.card label.dim-label`)

### bright green (`@text_active` / `@accent_color`)
Only for confirmed/active state.

- switch checked background
- active profile badge
- nightpanel toggle when on (`.nightpanel-toggle:checked`)
- slider fill (`scale trough highlight`)
- cheat sheet key labels (`.card label.monospace`)

### dim (`@text_dim`)
Ghost-level items — present but not primary.

- badge counts in nav sidebar
- card captions (`.card label.caption`)
- inactive tab labels (`.nightpanel-tab` default color)

---

## backgrounds

- **window**: `#0A0A0A`
- **cards / boxed lists**: `#111111`
- **header bar**: `#000000`
- **sidebar**: `#050505`
- **popovers**: `#1C1C1C`
- **switches (unchecked)**: `#2E2E2E`
- **key badges / keycaps**: `#1A1A1A`
- **comborow button**: `#222222`

No background on nav sidebar rows by default — transparent. Hover adds `alpha(@border_default, 0.25)`, selected adds `alpha(@border_selected, 0.12)` + `1px solid @border_quiet`.

---

## borders

Grey only — never accent-colored borders.

- quiet separators: `@border_quiet` (#2A2A2A)
- standard borders: `@border_default` (#383838)
- selected-state row border: `@border_quiet` (#2A2A2A) — subtle, not highlighted
- tab bar: inactive `@border_quiet`, active `@border_selected`

---

## component patterns

### tab bar (`.nightpanel-tab`)
- all-caps text via Python `.upper()` — the one intentional ALLCAPS surface
- `font-size: 0.72em`, `letter-spacing: 2px`
- inactive: `@text_dim` text, `@border_quiet` border
- active: `@text_primary` text, `@border_selected` border, `alpha(@border_selected, 0.08)` background fill
- hover: `alpha(@text_primary, 0.60)` text, `@border_default` border

### nav sidebar rows (`.navigation-sidebar listboxrow`)
- `border-radius: 6px`, `margin: 1px 4px`, `min-height: 32px`
- default: transparent background
- hover: `alpha(@border_default, 0.25)` background
- selected: `alpha(@border_selected, 0.12)` background + `1px solid @border_quiet` border

### nav sidebar section labels (`.sidebar-section-label`)
- `color: @text_primary`, `font-size: 0.70em`, `letter-spacing: 2px`
- used for "categories" and "settings" divider labels

### preferences groups
- title → `@text_primary`, `font-size: 0.70em`, `letter-spacing: 2px`
- description → `@text_secondary`

### shortcut rows (`.boxed-list`)
- title → `@text_primary`
- subtitle (description/schema path) → `@text_secondary`
- key badge background → `#1A1A1A`, border `@border_default`, text `@text_primary`

### cards (`.card`)
- heading → `@text_primary`
- monospace key labels → `@accent_color`
- dim-label → `@text_secondary`
- caption → `@text_dim`

### expanders (`Gtk.Expander`)
GTK 4.18 node structure: `expander-widget > box > title > { expander (arrow), label }`. Use `expander-widget title` to color the whole title row (arrow + text). Do NOT use `expander` as the top-level selector — that matches the arrow child node, not the widget.

### switches
- unchecked bg: `#2E2E2E`, slider: `#141414` with `1px solid #484848`
- checked bg: `@accent_bg_color`, slider: `#0A0A0A`

### brightness slider
- trough: `#2A2A2A`
- fill: `@accent_color`
- handle: `@text_primary`

---

## CSS implementation

All rules live in `src/dailydriver/services/theme_service.py → _build_theme_css()`.

Applied at `Gtk.STYLE_PROVIDER_PRIORITY_USER` (800) — high enough to override libadwaita defaults.

The brightness factor `b` (0.3–1.5) scales `@text_primary`, `@text_secondary`, `@text_active`, `@text_dim`, `@accent_color`, and `@accent_bg_color` via `_scale_hex()`. Background colors and borders are NOT scaled — they stay at their fixed dark values regardless of brightness.

---

## what to avoid

- no white text, ever
- no bold weight
- no accent color on borders or general backgrounds
- no Title Case or sentence case in labels — all lowercase
- no gradient fills
- no colored selection highlights (use grey border instead)
- do not use `@accent_color` for section headers or titles — that's reserved for confirmed/active state only
