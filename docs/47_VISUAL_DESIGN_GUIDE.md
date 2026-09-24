# AqOne Frontend Design System

> Status: implementation-derived single source of truth  
> Audited: 2026-08-03  
> Frontend surfaces: Flutter fisherman app and static regulator/admin web UI  
> Scope: visual language and UX behavior only

## 1. Purpose and precedence

This document records the frontend design actually implemented in the AqOne repository. It covers the Flutter application in mobile/ and the regulator-facing web experience in web/. It intentionally excludes network behavior, data models, storage, and all server-side concerns.

The product currently contains two related visual systems:

1. The Flutter app uses Material widgets with mostly inline values.
2. The regulator dashboard uses explicit CSS custom properties and a dense, glass-panel map interface.

Both share the same modern AqOne core: deep navy surfaces, blue brand actions, cyan accents, cool slate neutrals, rounded cards, and restrained shadows. The older web landing/login/terms pages use a separate, lighter blue-gray palette. The admin setup page is a third, isolated dark-teal treatment.

docs/archive/history/WEB_DASHBOARD_IMPROVEMENTS.md is historical commentary, not an active visual source. It describes an older dark-only dashboard and must not override the current CSS or this document.

For new work, use this precedence:

1. Use the canonical AqOne tokens in Section 2.
2. Use the component rules in Sections 6–10.
3. Preserve an exception only when working inside the legacy auth/terms or admin-setup surfaces documented here.
4. Do not introduce a new literal color, radius, font size, shadow, or breakpoint when an existing token serves the same purpose.

## 2. Color palette

### 2.1 Canonical brand and neutral colors

These values dominate both active frontend surfaces and are the preferred palette for new UI.

| Token | Hex | RGB | Role and current application |
|---|---:|---:|---|
| Brand deep | #0958A6 | 9, 88, 166 | Brand wordmark fallback, strong headings, dark blue emphasis |
| Brand primary | #0F69C9 | 15, 105, 201 | Primary buttons, active navigation, selected tabs, links, focused controls, map coverage |
| Sky accent | #38BDF8 | 56, 189, 248 | Dark-theme active controls, highlights, progress, selected icons |
| App navy | #0F172A | 15, 23, 42 | Flutter dark canvas and web dashboard dark background |
| Slate surface | #1E293B | 30, 41, 59 | Dark cards, dark headers, prominent dark text in light mode |
| Raised slate | #334155 | 51, 65, 85 | Dark secondary surfaces, selected navigation, dark borders |
| Slate text | #64748B | 100, 116, 139 | Secondary text, muted icons, inactive navigation |
| Muted slate | #94A3B8 | 148, 163, 184 | Placeholder text, metadata, tertiary content |
| Pale slate | #CBD5E1 | 203, 213, 225 | Dark-theme body text and subtle light dividers |
| Light border | #CFE8F9 | 207, 232, 249 | Pale input fills and light borders |
| Light accent border | #E3F5FF | 227, 245, 255 | Selected light navigation and subtle accent surface |
| Light blue surface | #E8F8FF | 232, 248, 255 | Informational cards and sidebar illustration surface |
| Light app canvas | #F4F8FA | 244, 248, 250 | Main Flutter and dashboard light background |
| White surface | #FFFFFF | 255, 255, 255 | Cards, controls, avatars, light-theme surfaces |

Canonical CSS definitions, as implemented in web/css/dashboard.css:

    :root {
      --bg: #F4F8FA;
      --surface: #FFFFFF;
      --surface-2: #B9E8FF;
      --border: #CFE8F9;
      --border-accent: #E3F5FF;
      --text: #1E293B;
      --text-secondary: #64748B;
      --text-dim: #94A3B8;
      --text-tertiary: #CBD5E1;
      --accent: #38BDF8;
      --primary: #0F69C9;
      --brand-deep: #0958A6;
      --blue-soft: #E8F8FF;
    }

### 2.2 Light and dark semantic mappings

| Semantic role | Light theme | Dark theme | Usage |
|---|---|---|---|
| Canvas | #F4F8FA | #0F172A | Screen/page background |
| Primary surface | #FFFFFF | #1E293B | Cards, panels, header surfaces |
| Secondary surface | #B9E8FF | #334155 | Stronger nested surface |
| Primary text | #1E293B | #F0F4F8 | Titles and body copy |
| Secondary text | #64748B | #94A3B8 | Labels, metadata, supporting copy |
| Dim text | #94A3B8 | #64748B | Placeholders and low-priority details |
| Tertiary text | #CBD5E1 | #CBD5E1 | Faint separators/labels |
| Border | #CFE8F9 | rgba(255,255,255,0.10) | General boundaries |
| Accent border | #E3F5FF | rgba(255,255,255,0.14) | Raised/selected boundaries |
| Glass panel | rgba(244,248,250,0.92) | rgba(30,41,59,0.85) | Header, dashboard panels, profile panels |
| Light glass | rgba(255,255,255,0.95) | rgba(255,255,255,0.88) | Inputs and light overlays |
| Glass border | rgba(15,105,201,0.12) | rgba(255,255,255,0.10) | Glass card outlines |
| Glass shadow | 0 8px 32px rgba(15,23,42,0.10) | 0 8px 32px rgba(0,0,0,0.45) | Standard elevated panel |

The Flutter equivalent is implemented directly in each screen:

    final canvas = isDark
        ? const Color(0xFF0F172A)
        : const Color(0xFFF4F8FA);
    final surface = isDark
        ? const Color(0xFF1E293B)
        : Colors.white;
    final active = isDark
        ? const Color(0xFF38BDF8)
        : const Color(0xFF0F69C9);

### 2.3 Semantic colors

| Meaning | Preferred value | Supporting values | Application |
|---|---:|---|---|
| Success / safe / online | #2ECC71 | #22C55E, #10B981, #16A34A, #27AE60 | Safe sea state, online buoys, completed actions, positive metrics |
| Warning / caution | #F59E0B | #F39C12, #F1C40F, #E67E22, #D97706 | Demo state, caution, pending review, weather advisory |
| Error / danger / SOS | #E74C3C | #EF4444, #DC2626, #C0392B, #8B0000, #FF4D4D | Emergency state, validation, critical markers, destructive actions |
| Information | #2E86AB | #3498DB, #0284C7, #3B82F6 | Informational advisory, facilities, map actions |
| Purple / model or buoy | #A78BFA | #9B59B6, #7C4DFF, #C4B5FD | Buoy markers, gradient avatars, model-assessment accents |
| Cyan / connectivity | #22D3EE | #00BCD4, #00D1FF, #4FC3F7 | Mesh links, pins, water/weather emphasis |
| Disabled / unknown | #94A3B8 | #9CA3AF, #95A5A6, #7F8C8D, #666666 | Offline, unavailable, unknown, secondary state |

Semantic colors are never the sole carrier of meaning. Pair them with an icon, label, badge text, border treatment, or shape. Current examples include SAFE TO SAIL, CAUTION, DO NOT SAIL, status dots, and alert headings.

### 2.4 Legacy web auth and terms palette

The landing, login, and terms surfaces predate the dashboard token set. Preserve these only while maintaining those pages.

| Value | Existing role |
|---:|---|
| #0D3B66 | Dark auth/terms brand blue |
| #2196C4 | Mid brand wordmark blue |
| #1565C0 | Auth primary button, link, focus border |
| #EAF4FF | Auth soft blue |
| #4F4F4F | Auth body text |
| #CCCCCC | Auth input border |
| #7B93B0 | Secondary/clear button |
| #E0E0E0 | Circular utility button |
| #0F4FA1 | Primary-button hover |
| #6D829B | Secondary-button hover |
| #1D354B, #1F405C | Terms body copy |
| #1E4B6E, #1D4E72, #3C5D7A | Terms metadata |
| #003759, #003D66, #004B7C, #0066B3 | Terms headings and links |
| #EAF2FA, #EEF4FA | Terms pill and divider backgrounds |

### 2.5 Admin setup exception palette

web/html/admin-signup.html is a self-contained dark setup form and does not consume the main design tokens.

| Value | Existing role |
|---:|---|
| #07131F | Page background and select-option text |
| #EEF7FF | Primary text |
| rgba(13,31,49,0.92) | Form card |
| rgba(238,247,255,0.72) | Supporting copy |
| #14B8A6 | Submit button |
| #03201D | Submit-button text |
| #FCA5A5 | Error message |
| #86EFAC | Success message |

New admin setup work should migrate to the canonical navy/blue/cyan palette rather than expand this exception.

### 2.6 Map and data-visualization colors

The regulator dashboard uses literal colors because map layers, generated markers, and data classifications need stable identities.

| Visual category | Values | Current meaning |
|---|---|---|
| Facilities | #3498DB | Facility marker and summary metric |
| Incidents / critical | #E74C3C | Incident marker, protected zone, emergency |
| Buoys | #9B59B6 | Buoy marker |
| Vessels | #22C55E or #38BDF8 | Generated marker and legend use different current values |
| Coverage circles | #60A5FA at 0.08 fill, 1.5px outline | Simulated coverage |
| Mesh links | #22D3EE at 0.45 opacity | Mesh topology |
| Mesh moving dot | #99F6E4 outline, #22D3EE fill | Connectivity animation |
| Aklan boundary | #2ECC71, 2.5px, 0.06 fill | Geographic boundary |
| Prediction scale | #95A5A6, #3498DB, #2ECC71, #F1C40F, #E67E22, #E74C3C | Unknown/very low through critical |
| Pin identity palette | #00BCD4, #E91E63, #FF9800, #8BC34A, #673AB7, #009688, #FF5722, #3F51B5, #CDDC39, #F06292 | Deterministic user pin colors |
| Advisory information | #2E86AB | Information priority |
| Advisory community | #27AE60 | Community priority |

Do not reuse prediction colors for unrelated categories in the same view. Map legends must show the exact visible color and label.

### 2.7 Complete literal-color inventory

The following normalized values account for the explicit hexadecimal colors in Flutter Dart and the web HTML/CSS/visual JavaScript. Duplicate shorthand such as #FFF and #FFFFFF is shown once. Alpha versions are listed separately below.

Brand/blues:

#003759, #003D66, #004B7C, #0066B3, #0066EE, #0072FF, #0077FF, #009688, #00BCD4, #00C6FF, #00D1FF, #0284C7, #0958A6, #0B4C8C, #0D3B66, #0F4FA1, #0F69C9, #14B8A6, #1565C0, #1D4E72, #1E4B6E, #1E5B99, #2196C4, #22D3EE, #2E86AB, #3498DB, #38BDF8, #3B82F6, #3F51B5, #4FC3F7, #5AB6E5, #60A5FA, #673AB7, #7C4DFF, #7CBFE6, #99F6E4, #9B59B6, #A78BFA, #B9E8FF, #C4B5FD, #CFE8F9, #E3F5FF, #E5F4FC, #E8F8FF, #EAF2FA, #EAF4FF.

Green/success:

#03201D, #064E3B, #10B981, #16A34A, #22C55E, #27AE60, #2E7D32, #2ECC71, #4CAF50, #69F0AE, #86EFAC, #8BC34A, #CDDC39, #ECFDF5.

Amber/orange/warning:

#D97706, #E67E22, #F1C40F, #F39C12, #F59E0B, #FF9800, #FFA000, #FFAB40, #FFC107, #FFD54F, #FFFDF0.

Red/pink/danger:

#7F1D1D, #8B0000, #C0392B, #C62828, #DC2626, #E74C3C, #E91E63, #EF4444, #F06292, #F44336, #FCA5A5, #FEF2F2, #FF4D4D, #FF5252, #FF5722.

Neutrals:

#000000, #07131F, #0F172A, #1A1A2E, #1D354B, #1E293B, #1F405C, #2C4960, #334155, #3C5D7A, #475569, #4A6B82, #4F4F4F, #5A7E97, #64748B, #666666, #6B7280, #6D829B, #757575, #7A97AC, #7B93B0, #7F8C8D, #90A4AE, #94A3B8, #95A5A6, #9CA3AF, #9E9E9E, #B0BEC5, #BDBDBD, #CBD5E1, #CCCCCC, #D4E2EC, #E0E0E0, #E2E8F0, #E2EFF9, #E8F0F8, #EEF4FA, #EEF7FF, #F0F4F8, #F1F5F9, #F4F8FA, #F8FAFC, #FFFFFF.

Flutter also uses Material named colors and opacity constants. Their effective base colors include black, white, transparent, Grey 500 #9E9E9E, Grey 400 #BDBDBD, Grey 600 #757575, Blue 500 #2196F3, Green 500 #4CAF50, Red 500 #F44336, Red 800 #C62828, Green 800 #2E7D32, Amber 500 #FFC107, Amber 300 #FFD54F, Amber 700 #FFA000, Red Accent #FF5252, Green Accent #69F0AE, Orange Accent #FFAB40, and Light Blue Accent 100 #80D8FF. Flutter platform chrome additionally retains the template blue #0175C2 in mobile/web/manifest.json.

Normalized alpha overlays observed in the web UI:

- Black: rgba(0,0,0,0.15), 0.20, 0.25, 0.28, 0.30, 0.35, 0.38, 0.40, 0.45, 0.50, and 0.60.
- White: rgba(255,255,255,0.03), 0.04, 0.05, 0.06, 0.08, 0.10, 0.12, 0.14, 0.15, 0.18, 0.20, 0.25, 0.35, 0.40, 0.45, 0.60, 0.70, 0.85, 0.88, 0.90, and 0.95.
- Brand blue #0F69C9: alpha 0, 0.08, 0.10, 0.12, 0.14, 0.16, 0.20, 0.25, and 0.40.
- Legacy primary #1565C0: alpha 0.05, 0.12, and 0.16.
- Danger #E74C3C: alpha 0.05, 0.08, 0.10, 0.15, 0.16, 0.18, 0.20, 0.25, 0.30, 0.35, and 0.90.
- Success #2ECC71: alpha 0.08, 0.18, 0.20, 0.22, 0.25, and 0.55.
- Yellow #F1C40F: alpha 0.08, 0.18, 0.20, and 0.25.
- Orange #F39C12: alpha 0.06, 0.10, 0.12, 0.15, 0.20, and 0.25.
- Amber #F59E0B: alpha 0.14, 0.16, 0.22, 0.28, and 0.35.
- Cyan #22D3EE: alpha 0.08, 0.10, and 0.30.
- Purple #8B5CF6: alpha 0.15 and 0.25.

Eight-digit CSS values #2ECC7140, #F1C40F40, and #E74C3C40 are 25% alpha outlines.

### 2.8 Gradient inventory

Gradients are accents, not substitutes for the core surface hierarchy.

| Surface | Stops / direction | Use |
|---|---|---|
| Flutter sign-up fallback | #FFFDF0 → #E5F4FC → #7CBFE6 | Full-screen auth background when the photograph is unavailable |
| Flutter profile rating badge | #00C6FF → #0072FF | Circular score/avatar treatment |
| Flutter quick-stat card, light | #B9E8FF → #E8F8FF | Low-emphasis analytics card |
| Flutter quick-stat card, dark | #1E293B → #0F172A | Dark counterpart to the analytics card |
| Flutter Venture central action | #5AB6E5 → #1E5B99 | Primary floating map action |
| Flutter chart area | #0072FF or #38BDF8 at 25% → transparent | Area fill under line charts, selected by theme |
| Web avatar | #38BDF8 → #A78BFA | Profile/avatar placeholder |
| Web profile cover | #0F69C9 → #38BDF8 | Profile hero strip |
| Web warning banner | rgba(245,158,11,0.22) → rgba(249,115,22,0.14) | Operational warning banner |
| Web auth overlay | translucent white → deep blue on a diagonal | Preserves foreground contrast over video |

Keep gradient text and essential labels out of these treatments unless contrast is verified against every stop.

## 3. Typography

### 3.1 Font families and sources

| Surface | Declared stack | Source and actual behavior |
|---|---|---|
| Web dashboard/profile | "Inter", "Segoe UI", Roboto, system-ui, -apple-system, sans-serif | No Inter import, @font-face, or bundled font exists. Inter appears only when installed locally; Windows normally resolves to Segoe UI. |
| Web landing/login/terms | "Segoe UI", Roboto, Arial, sans-serif | System-font stack; no downloaded font. |
| Admin setup | Arial, sans-serif | Self-contained inline style. |
| Dashboard telemetry | "Consolas", "SF Mono", monospace | Coordinates, phone numbers, identifiers, and numeric telemetry. |
| Flutter | Material default typography | No custom fontFamily or font assets. Flutter resolves its platform Material defaults; visual metrics may differ by platform. |
| Icons | Material Icons in Flutter; inline SVG on web | Material icon font is enabled by uses-material-design. |

Cupertino Icons is declared as a Flutter dependency but is not used in the audited Dart source.

### 3.2 Canonical type hierarchy

The implementation does not define a formal modular scale. It uses fixed values optimized separately for mobile content and the dense desktop dashboard.

| Role | Flutter | Web dashboard/profile | Weight | Line height / tracking |
|---|---:|---:|---:|---|
| Display / auth title | 28–32px | 24–32px | 700–900 | Usually 1.0–1.25; heading tracking -0.5px to -0.02em |
| Screen title | 26–28px | 21–26px | 800–900 | -0.5px where specified |
| Section title | 18–22px | 15–18px | 700–800 | 0–0.4px |
| Card title | 14–18px | 12–16px | 600–700 | 1.2–1.3 |
| Body | 14–16px | 12–15px | 400–600 | 1.3–1.6 |
| Supporting body | 12–14px | 11–13px | 400–600 | 1.3–1.5 |
| Caption / metadata | 10–12px | 9–11px | 500–700 | Often 0.3–0.6px |
| Badge / eyebrow | 8–11px | 7–10px | 700–800 | Uppercase, 0.3–0.8px |
| Telemetry | 10–13px | 10–13px monospace | 600–700 | 0.3px |

Flutter explicit sizes in use: 8, 9, 10, 10.5, 11, 12, 13, 14, 15, 16, 17, 18, 20, 22, 24, 26, 28, and 32px.

Web explicit sizes in use: 7, 8, 9, 10, 10.5, 11, 11.5, 12, 13, 13.5, 14, 14.5, 15, 16, 16.5, 18, 20, 21, 22, 23, 24, 26, 32, and 38px, plus 0.75, 0.9, 0.95, 0.98, 1, 1.02, 1.2, and 1.6rem on auth/terms pages.

### 3.3 Typography rules

- Use sentence case for user-facing titles and actions.
- Reserve uppercase for compact operational labels, badges, panel headers, and status language.
- Use weight 700 for actionable labels; 800–900 only for screen titles, critical numeric values, and strong profile identity.
- Use Slate #64748B/#94A3B8 for metadata, never reduced opacity alone when readability matters.
- Use monospace only for coordinates, identifiers, phone numbers, and sensor-like values.
- Keep body line height between 1.4 and 1.6. Dense dashboard labels may use 1.0–1.3.
- New screen titles should use 28px/900 in Flutter or 24px/700–800 on web unless constrained by the dense dashboard.

## 4. Layout and grid system

### 4.1 Flutter application shell

At widths below 900px, the primary app uses a mobile/tablet stack:

- Full-width screen content.
- Scrollable body with 16–24px horizontal padding.
- 110px bottom content allowance where the floating navigation overlaps.
- A 78px bottom dock with 24px top corner radii.
- Home and Settings flank a raised 66px circular Venture action.

At 900px and above:

- A fixed 250px left navigation sidebar.
- Main content fills remaining width.
- Home content changes to a 3:2 two-column card layout with a 20px gutter.
- The desktop top bar uses 24px horizontal and 16px vertical padding.
- Settings, Dashboard, and Advisories also use 900px as their desktop breakpoint.

Venture Mode uses a separate 800px header breakpoint. Its core content is a full-bleed map with floating controls:

- Weather/status capsule: 12px below the header, 18px horizontal margins.
- Right action stack: 16px from the right, 24px from the bottom.
- Checklist overlay: 16px from each side, 95px above the bottom.
- Map zoom range is a visual interaction constraint; overlays must remain legible above the basemap.

Login and sign-up use:

- Full-screen portrait background image with BoxFit.cover.
- Centered, vertically scrollable form.
- Maximum content width 420px.
- 24px horizontal and 20px vertical viewport padding.
- Tablet/desktop threshold at widths greater than 600px.

Contact tiles switch to a two-column grid when the screen is desktop or the available card width exceeds 550px; tiles use a fixed 82px main-axis extent.

### 4.2 Web landing, login, and terms

Landing/login:

- Full-viewport background video and 16:9 poster using object-fit: cover.
- Centered flex shell with 24px page padding.
- Content width min(100%, 600px).
- Frosted card with 20px radius and 28px 24px padding.
- At 480px or below, shell padding drops to 16px and button/footer rows stack.

Terms:

- Centered page with max-width 950px and 24px page padding.
- Main card padding 2rem 2.2rem, falling to 1.5rem 1.1rem at 640px.
- Two-column 1fr/1fr terms grid with 2rem column gutter.
- Grid becomes one column at 700px.

### 4.3 Regulator map dashboard

Desktop/tablet shell:

- Fixed 68px glass header.
- Fixed 36px alert/demo banner immediately below it.
- Body begins at header + banner height.
- Map consumes flexible remaining width.
- Right panel is fixed at 380px, with 8px outer padding and 8px vertical gaps.
- At 1024px and below, panel width becomes 320px and search max-width becomes 240px.
- The header search otherwise has a 380px maximum.

At 768px and below:

- The entire right panel is hidden.
- Header map-layer controls and search are hidden.
- Banner grows to a minimum of 52px with wrapped centered text.
- Map becomes the sole body surface.

At 480px and below:

- Header title becomes 13px.
- Subtitle, user name, and demo sync pill disappear.
- User pill collapses to avatar only.

The dashboard is flex-driven rather than a formal column grid. The comments describe an approximate 68/32 map-panel split, but the implementation uses a fixed panel and fluid map.

### 4.4 Web profile layout

- Maximum canvas width: 1480px.
- Desktop shell: horizontal flex, 28px gap, padding 40px clamp(20px, 5vw, 64px).
- Left profile rail: 400px, sticky below the header.
- Main profile content: flexible width with 22px vertical gaps.
- At 1100px: rail becomes 340px; shell gaps/padding tighten.
- At 860px: layout stacks vertically and sticky positioning is removed.
- Personal-information form: two equal columns with 22px row and 24px column gaps.
- At 640px: form becomes one column with a 16px gap.
- At 480px: panel padding and tabs compress; action buttons expand evenly.
- Profile statistics use a three-column equal grid.

### 4.5 Breakpoint reference

| Breakpoint | Surface | Behavior |
|---:|---|---|
| >600px | Flutter auth | Uses fixed desktop/tablet logo sizes |
| >550px available | Flutter contacts | Two-column contact grid |
| >=800px | Flutter Venture header | Desktop-aligned header behavior |
| >=900px | Flutter app | 250px sidebar and desktop content composition |
| <=1100px | Web profile | Narrower rail and shell |
| <=1024px | Web dashboard | 320px right panel |
| <=860px | Web profile | Stacked profile layout |
| <=768px | Web dashboard | Map-only; panel and major controls hidden |
| <=700px | Web terms | One-column terms grid |
| <=640px | Web terms/profile | Compact terms card; one-column profile form |
| <=480px | Web shared | Compact auth, header, profile actions |

## 5. Spacing and sizing scale

### 5.1 Base scale

No shared spacing token file exists. The dominant rhythm is a 4px base grid:

| Step | Value | Typical use |
|---:|---:|---|
| 0.5 | 2px | Micro-label separation and active underline |
| 1 | 4px | Icon-label gaps, compact badge padding |
| 1.5 | 6px | Dense dashboard gaps |
| 2 | 8px | Standard compact gap, panel spacing |
| 2.5 | 10px | Input/card internal gap |
| 3 | 12px | Default card and row gap |
| 3.5 | 14px | Input vertical padding |
| 4 | 16px | Standard content/card padding |
| 4.5 | 18px | Profile and floating-map margins |
| 5 | 20px | Major card gutter |
| 6 | 24px | Screen padding and section spacing |
| 7 | 28px | Auth section and profile shell gap |
| 8 | 32px | Large panel padding |
| 10 | 40px | Desktop shell/brand separation |
| 12 | 48px | Empty/loading-state breathing room |

Values such as 5, 7, 9, 11, 13, 22, 26, and 30px are implementation exceptions, mostly in the dense dashboard/profile UI.

### 5.2 Common control and container sizes

| Element | Size |
|---|---|
| Flutter mobile brand images | 34px high each |
| Flutter header/profile avatar | 38 × 38px |
| Flutter desktop sidebar | 250px wide |
| Flutter desktop search shell | 48px high |
| Flutter floating dock | 78px high |
| Flutter Venture center action | 66 × 66px |
| Flutter map utility control | 40–44px square |
| Flutter profile avatar | 120–125px |
| Web dashboard header | 68px high |
| Web alert banner | 36px; 52px minimum on mobile |
| Web right panel | 380px; 320px at <=1024px |
| Web header icon controls | 36–38px square |
| Web toolbox control | minimum 56 × 44px |
| Web profile rail | 400px; 340px at <=1100px |
| Web profile avatar | 116 × 116px |
| Web modals | 400, 420, 450, or 520px; max 90–92vw |
| Auth card | 600px max web; 420px max Flutter |

## 6. UI components and patterns

### 6.1 Buttons

Primary:

- Brand primary #0F69C9 background, white label.
- 10px Flutter radius or 6–8px web dashboard radius.
- 14–16px label at weight 700 in Flutter; 12–13px/700 in dense web controls.
- Typical vertical padding: 14px Flutter, 8–12px web.
- Hover on web darkens to #0958A6 or reduces opacity to 0.85.
- Flutter uses Material press/ripple behavior when ElevatedButton, OutlinedButton, TextButton, or IconButton is used.

Secondary/ghost:

- Transparent, border-colored, pale blue-gray, or low-opacity white background.
- Text uses primary blue or current theme text.
- Hover raises the background alpha from approximately 0.06 to 0.12.

Danger/destructive:

- #E74C3C or #DC2626 fill; white text.
- Low-emphasis destructive actions use red text, a red-tinted background, and a red border.
- Never use danger styling for ordinary cancellation.

Icon buttons:

- 36–44px square preferred.
- Circular for identity, back, and notification actions; 8–12px rounded square for utilities.
- Icons inherit currentColor on web and use explicit Material colors in Flutter.

Disabled:

- Admin setup explicitly uses opacity 0.6 and not-allowed cursor.
- Several dashboard controls are disabled by state but lack a universal CSS disabled selector.
- Flutter Material buttons use framework disabled treatment; custom GestureDetector controls have no automatic disabled appearance.

### 6.2 Inputs and form fields

Flutter auth:

- Filled with #CFE8F9 at 55% opacity.
- 10px radius.
- 16px horizontal and 14px vertical content padding.
- Text 15px #2C4960; placeholder 14px #7A97AC.
- Enabled border: 1px translucent white.
- Focus: 1.5px #0F69C9.
- Error: 1px Red Accent, 1.5px when focused.
- Prefix/suffix icons: 20px #4A6B82.

Web auth:

- White background, 1px #CCCCCC border, 8px radius.
- 12px padding and 14px text.
- Focus: #1565C0 border plus 3px rgba(21,101,192,0.16) ring.

Dashboard/profile:

- Theme surface/glass background.
- 1px theme border, 6–8px radius.
- Focus changes border to #0F69C9; dashboard search additionally uses the cyan glow token.
- Profile fields use 14px 17px padding and 16px text.
- Dashboard modal fields use 9px 10px padding and 13px text.
- Textareas may resize vertically; options use the theme surface.

### 6.3 Cards and panels

Canonical dashboard panel:

    .panel-card {
      background: var(--glass-bg);
      backdrop-filter: blur(16px) saturate(180%);
      border: 1px solid var(--glass-border);
      border-radius: 12px;
      box-shadow: var(--glass-shadow);
      overflow: hidden;
    }

- Header: 12px 16px padding, uppercase 12px/700, 0.4px tracking.
- Body: 14px 16px padding.
- Nested compact cards use 8px radius, 8–14px padding, and theme borders.

Flutter card convention:

- White light surface or #1E293B dark surface.
- Large Home cards use 24px radius; Settings uses 20px; Advisories and many nested data cards use 16px; map/control cards use 12px.
- Outer screen/card margins are normally 16–24px.
- Shadow is subtle in light mode and stronger in dark mode.
- Cards place an icon/title row first, followed by content and optional metadata/actions.

### 6.4 Navigation

Flutter desktop:

- 250px white/#1E293B sidebar.
- Active row uses #E3F5FF light or #334155 dark and active blue/cyan text.
- 12px row radius.
- Home, Venture Mode, and Settings are the active information architecture.

Flutter mobile:

- White/#1E293B dock with 24px top radii.
- Home and Settings use 26px Material icons and 11px labels.
- Active is #0F69C9 light or #38BDF8 dark.
- Venture is a raised location action with #5AB6E5 to #1E5B99 gradient.

Web dashboard:

- Header holds brand, basemap segmented controls, search, sync/demo status, theme/fullscreen controls, and user identity.
- Right-panel toolbox uses horizontally scrolling 56 × 44px tools.
- Active tools receive blue-tinted background, primary text, and a 2px bottom indicator.
- Tabs use active filled color and compact status badges.

### 6.5 Modals, drawers, sheets, and toasts

Web modals:

- Full-screen rgba(0,0,0,0.60) overlay.
- 12px modal radius and 0 20px 60px rgba(0,0,0,0.50) shadow.
- Closed state: opacity 0 plus scale 0.95.
- Open state: opacity 1 plus scale 1 over 200ms ease.
- Header/body padding follows 18–20px.
- Widths: emergency 420px, advisory 520px, small confirmation 400px. A 450px assessment modal and a separate BFAR modal are fully styled in CSS but dormant because current dashboard HTML has no matching modal elements.
- Maximum height 85–88vh where content scrolls.

SOS drawer:

- Slides from the right; becomes full-width at 768px.
- Header color communicates SOS, wave, capsizing, or overdue status.
- Action order runs from neutral zoom to warning acknowledge, success resolve, and brand broadcast.

Flutter:

- AlertDialog typically uses a 20px radius and themed surface.
- Modal bottom sheets respect keyboard insets and use a short centered drag handle.
- SnackBars provide brief system feedback.

Toasts:

- Web toast enters/exits with a 300ms slide.
- Maximum width is 340px.
- Success title uses #2ECC71; container uses themed surface and shadow.

### 6.6 Status, badges, empty, and loading states

- Status badges are compact pills: 2–8px horizontal padding, 5–10px radius, 8–12px bold text.
- Safe/online uses green tint; caution/pending amber; danger/active red; neutral/unknown slate.
- Loading uses circular spinners, pulsing dots, italic status copy, or a full overlay.
- Empty states center an outline icon, title, supporting copy, and optional action with 20–48px internal space.
- Offline/stale content is visually reduced but should remain readable.

### 6.7 Maps and operational overlays

- Map is full bleed; controls float on glass surfaces so the basemap remains visible.
- Coordinates use a bottom-centered monospace pill.
- Compass/home control uses a 40–44px circular/square glass button.
- Markers use color plus distinct symbol/shape.
- User pins are rotated square map pins with hover scale.
- Coverage is low-alpha fill; topology is a dashed/animated cyan line.
- Critical overlays pulse sparingly; standard data markers should remain static.
- Every data layer visible to a user needs a matching legend entry.

### 6.8 Trust badges and plausibility tags (frozen 2026-09-24)

Frozen by `docs/62_EDGE_CASE_REMEDIATION_IMPLEMENTATION_PLAN.md` Phase 0; built in Track W phases W3 and W4.
These rules override 6.6 wherever they overlap.

**Trust badges are positive only (EC-H10).**

- A vessel with `vessel_verified = true` shows one green-tint pill: "Verified by MDRRMO".
- Every other vessel shows plain neutral grey text, "not yet verified", with no pill, no icon and no colour.
- Never show a yellow, amber or red badge for trust, and never an "unregistered" or "unverified" badge.
- Trust tier never changes card colour, sort order, alarm or any other priority signal.
  A call from an unknown boat looks and rings exactly like one from a verified boat.
- `license_type` text never produces a badge.
- A phone number with `phone_set_by = anonymous` is followed by neutral grey text "(unverified number)".

**Plausibility tags are advisory (EC-H20).**

- Each entry in an event's `flags` (`docs/05` E5.4) renders as a small neutral tag: slate text on a slate tint, the 6.6 pill size, no icon.
- Tags never use the danger, caution or safe colours, never pulse, and never change card colour or order.
- Labels:

  | Flag | Label |
  | --- | --- |
  | `position_on_land` | "Position on land" |
  | `position_beyond_radio_range` | "Beyond radio range" |
  | `position_jump` | "Position jumped over 20 km" |
  | `many_calls_same_vessel` | "Several calls from this vessel" |
  | `position_conflict` | "Conflicting positions" |

- The conflicting second position is a hollow marker of the same shape as the primary, with the tooltip "conflicting position".
- A late call shows "LATE - pressed 3 d 4 h ago" in the same neutral tag style; it is information, not a lower priority.

## 7. Iconography

### 7.1 Flutter

- Primary library: built-in Material Icons.
- Style preference: rounded and outlined variants for friendly utility UI.
- Common sizes: 14–18px for badges/meta, 20–24px for controls, 26–32px for navigation/actions, 40–80px for empty states or illustration fallbacks.
- Active icons use #0F69C9 in light mode and #38BDF8 in dark mode.
- Inactive icons use #7A97AC/#64748B or Material black/white opacity variants.
- Semantic icons use their state color, always paired with a text label for critical information.
- A few custom PNG navigation icons exist, but the current primary navigation uses Material icons.

### 7.2 Web

- No external icon font is used.
- Dashboard/profile icons are inline 24 × 24 viewBox SVGs, normally rendered at 14, 16, 18, 20, or 22px.
- Standard stroke is currentColor at 2px; emphasis sometimes uses 2.2 or 2.5px.
- SVG fill is usually none, with round caps/joins where appropriate.
- Inline SVG must inherit currentColor so theme and component states control it.
- Decorative SVG may be lower opacity; semantic and actionable SVG must not be faded below readable contrast.

## 8. Imagery and illustrations

### 8.1 Runtime Flutter assets

Only the following are declared for runtime use in mobile/pubspec.yaml:

| Asset | Intrinsic size | Use |
|---|---:|---|
| assets/images/background.png | 875 × 1797, 0.487 ratio | Full-screen auth background, BoxFit.cover |
| assets/icons/aqoneLogo2.png | 358 × 338, near-square | Mascot/logo mark; BoxFit.contain |
| assets/icons/aqoneLogo3.png | 419 × 136, 3.081 ratio | AqOne wordmark; BoxFit.contain |
| assets/icons/emptyProfile.png | 500 × 500, square | Circular avatar fallback; BoxFit.cover |

aqoneLogo3.png appears twice in pubspec and should be treated as one asset.

Profile images:

- Render in ClipOval/CircleAvatar.
- Use BoxFit.cover.
- Fall back to emptyProfile.png, then a person icon on #D4E2EC light or #334155 dark.
- Typical visible size is 38px in headers and 116–125px on profile surfaces.

### 8.2 Web assets

| Asset | Intrinsic size | Use |
|---|---:|---|
| assets/pic/bg.png | 1920 × 1080, 16:9 | Video poster and static auth/terms fallback |
| assets/vid/bgvid.mp4 | 13.9 MB | Fixed full-screen auth/terms background |
| assets/icons/logo.png | 80 × 80 | Landing card logo |
| assets/icons/logonotext.png | 40 × 40 | Compact logo option |
| assets/icons/aqoneLogo2.png | 358 × 338 | Dashboard/profile top logo |
| favicon and 192/512 icons | Square | Browser/PWA identity |

Video/image treatment:

- Position fixed, inset 0, 100% width/height.
- Use object-fit: cover and center alignment.
- Place behind content at z-index -2.
- Apply a white wash and diagonal blue-white overlay so text remains readable.
- Content sits on a 90% white card with a translucent border.

The landing logo source is only 80 × 80px but style.css renders it at 350px wide. Treat this as a current implementation defect; do not use that upscale ratio for new raster artwork.

### 8.3 Reference-only assets

docs/design-reference/finalDesign, finalMobileApplication, finalDesktopApplicaation, wireframes, and files such as dashboardDesign.png/homeDesign.png/newsDesign.png are design references, not declared runtime assets. Their dominant reference ratios are:

- Mobile finals: approximately 0.462 (about 853 × 1844).
- Desktop finals: approximately 1.5 (typically 1536 × 1024).
- Wireframes: approximately 0.53 portrait.

Do not render reference mockups inside the product. Use them only to validate intent.

The current Venture hotspot model receives a proof-image reference but does not render that image. Do not infer a hotspot-photo card style from the present UI.

### 8.4 Imagery rules

- Logos and wordmarks always use contain; never crop or stretch.
- User-generated/profile imagery always uses cover inside a clipped frame.
- Full-screen scenic imagery uses cover with an overlay.
- Preserve square aspect ratios for avatars and icons.
- Use 12–20px radii on rectangular illustration containers.
- Always provide an icon or local-asset fallback for failed image loads.

## 9. Shadows, borders, radius, and effects

### 9.1 Radius scale

| Token | Value | Use |
|---|---:|---|
| Radius micro | 3–4px | Progress bars, underlines, tiny tags |
| Radius compact | 6px | Dense buttons, modal fields, badges |
| Radius small | 8px | Inputs, utility buttons, nested cards |
| Radius default | 12px | Dashboard panels, modals, standard cards |
| Radius medium | 16px | Flutter cards, profile grouping |
| Radius large | 20px | Auth/terms cards, dialogs |
| Radius dock | 24px | Flutter bottom dock and large pills |
| Radius pill | 30px or 999px equivalent | Status pills, toggles, capsules |
| Radius circle | 50% / BoxShape.circle | Avatars, marker dots, icon buttons |

Flutter has literal radii 2, 4, 6, 8, 10, 12, 14, 15, 16, 20, 24, and 30px. The web additionally uses 1, 3, 5, 6, 8, 9, 10, 12, 14, 16, 20, and 30px. Prefer 4/8/12/16/20/24/30 for new work.

### 9.2 Border rules

- Standard boundary: 1px.
- Focus and map coverage: 1.5px.
- Strong semantic selection: 2px.
- Avatar ring: 3–5px.
- Use theme border tokens rather than hard white alpha wherever possible.
- Use a colored left border (3px) to classify dense alert/contact cards.
- Inputs must retain a visible focus boundary in both themes.

### 9.3 Elevation and shadows

| Preset | Value | Use |
|---|---|---|
| Glass panel light | 0 8px 32px rgba(15,23,42,0.10) | Dashboard/profile cards |
| Glass panel dark | 0 8px 32px rgba(0,0,0,0.45) | Dark dashboard/profile cards |
| Auth card | 0 16px 40px rgba(13,59,102,0.12) | Landing/login/terms |
| Header | 0 2px 20px rgba(0,0,0,0.25) | Fixed dashboard header |
| Floating control | 0 4px 12px rgba(0,0,0,0.15) | Map pills and active controls |
| Modal | 0 20px 60px rgba(0,0,0,0.50) | Web modal dialogs |
| Flutter light card | black at 0.03–0.06, blur 6–20, offset 0 2–4 | Light cards |
| Flutter dark card | black at 0.20–0.30, blur 6–20, offset 0 2–4 | Dark cards |
| Floating dock | black at 0.04 light / 0.30 dark, blur 20, offset 0 -8 | Mobile navigation |

### 9.4 Glass and overlay effects

- Dashboard header: blur(20px) saturate(180%).
- Dashboard/profile cards: blur(16px) saturate(180%).
- Map pills/controls: blur(12px); attribution uses blur(4px).
- Modal scrim: black at 60%.
- Background-video overlay: white at 12% plus a diagonal white/deep-blue gradient.
- Avoid backdrop blur without a translucent fill and border; all three are part of the glass treatment.

## 10. Motion and transitions

### 10.1 Timing tokens

| Duration | Use |
|---:|---|
| 150ms ease | Dense hover, color, border, opacity |
| 180ms ease | Navigation/tool/profile hover |
| 200ms ease | Standard button, input, modal, theme-control transition |
| 250–300ms ease | Banner, collapse, toast, card entrance |
| 400–600ms ease | Progress/data entrance and hotspot fade |
| 800ms linear | Loading spinner |
| 1.5–2s ease-in-out infinite | Alert, buoy, sync, and connectivity pulse |

Web named animations include sync-pulse, banner-blink, wc-dot-pulse, wc-dot-pulse-danger, buoy-pulse, spin, buoy-dot-pulse, gateway-pulse, overdue-badge-pulse, overdue-ring-pulse, ai-spin, ai-fade-slide, bfar-card-fade, toast-slide, and hotspot-fade-in.

Flutter custom motion includes:

- Sign-up success: 600ms elasticOut scale.
- Venture connectivity/status animation: 2200ms controller.
- Venture visibility fade: 180ms.
- Standard Material navigation, ripple, dialog, and route transitions.

Motion rules:

- Use pulse only for changing/urgent operational status.
- Never pulse large surfaces.
- Default interaction motion is 150–200ms ease.
- Modal scale should remain subtle: 0.95 to 1.
- Preserve meaning when animations are unavailable; labels and static colors must still communicate state.
- The current CSS has no prefers-reduced-motion override. Add one before expanding animation usage.

## 11. Design tokens and theming

### 11.1 Web theming

The dashboard and profile switch themes by setting data-theme="dark" on the root element. Theme choice is stored under aqone-theme in localStorage. profile.css depends on dashboard.css being loaded first.

The token groups are:

- Color: --bg, --surface, --surface-2, --border, --border-accent, --text, --text-secondary, --text-dim, --text-tertiary.
- Brand: --accent, --accent-glow, --primary, --brand-deep, --blue-dark, --blue-mid, --blue-primary, --sky-accent, --blue-soft.
- Semantic: --danger, --warning, --success, --purple.
- Glass: --glass-bg, --glass-bg-light, --glass-border, --glass-shadow.
- Shape: --radius: 12px and --radius-sm: 8px.
- Layout: --header-h: 68px, --banner-h: 36px, --panel-w: 380px.

Landing/login/terms are light-only. Admin setup is dark-only.

### 11.2 Flutter theming

Flutter uses a global ValueNotifier<ThemeMode> initialized to ThemeMode.light. MaterialApp binds:

    theme: ThemeData.light()
    darkTheme: ThemeData.dark()
    themeMode: appThemeNotifier.value

Most primary screens then calculate isDark and provide explicit AqOne colors. The custom theme is held in memory only; it is not persisted. Auth and sign-up remain visually light because their background imagery and fields are explicitly styled.

There is no shared Flutter ThemeExtension, ColorScheme, TextTheme, spacing class, or component-theme layer. The repeated values in Section 2 are therefore the normative token set until they are centralized in code.

### 11.3 Cross-platform token contract

New components should map the same semantic roles:

| Role | Flutter | Web |
|---|---|---|
| Canvas | Color(0xFFF4F8FA) / Color(0xFF0F172A) | --bg |
| Surface | Colors.white / Color(0xFF1E293B) | --surface |
| Primary action | Color(0xFF0F69C9) | --primary |
| Dark-theme active | Color(0xFF38BDF8) | --accent |
| Primary text | Color(0xFF1E293B) / Colors.white | --text |
| Secondary text | Color(0xFF64748B) / Color(0xFF94A3B8) | --text-secondary |
| Border | Color(0xFFCFE8F9) / Color(0xFF334155) | --border |
| Standard radius | BorderRadius.circular(12) or 16 for mobile cards | --radius |
| Compact radius | BorderRadius.circular(8) | --radius-sm |

## 12. Global styles and reset

### 12.1 Web dashboard/profile

dashboard.css applies:

    *, *::before, *::after {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }

    html, body {
      height: 100%;
      overflow: hidden;
      font-family: "Inter", "Segoe UI", Roboto, system-ui,
                   -apple-system, sans-serif;
      color: var(--text);
      background: var(--bg);
      -webkit-font-smoothing: antialiased;
    }

profile.css overrides the body to auto height and vertical scrolling. No third-party reset/normalize package is loaded.

### 12.2 Web auth and terms

- style.css sets box-sizing: border-box globally but does not reset every margin/padding.
- terms.css resets margin, padding, and box-sizing for all elements.
- Both set body margin explicitly and use system fonts.
- color-scheme: light is declared for these surfaces.
- Horizontal overflow is suppressed on auth pages.

### 12.3 Flutter

MaterialApp and ThemeData provide the framework baseline. There is no custom global TextTheme or ComponentTheme. Individual screens control SafeArea, scroll physics, background, input decoration, and card styling.

Flutter web and native startup chrome are not yet aligned with the in-app system:

- mobile/web/manifest.json uses template theme/background color #0175C2 and forces portrait-primary.
- Android startup is plain white/system background.
- iOS startup is the default white launch screen; its launch-image PNGs are 1 × 1 placeholders.
- Flutter web defines no additional reset, font loading, or smoothing CSS.

## 13. Interaction, responsiveness, and UX conventions

- All full-screen Flutter screens begin inside SafeArea.
- Long mobile content scrolls with BouncingScrollPhysics.
- Desktop navigation remains visible; mobile navigation is thumb-reachable at the bottom.
- Critical actions such as SOS and logout use confirmation or prominent semantic treatment.
- Profile avatars are consistently interactive identity entry points.
- Search fields appear in several headers; where a search is decorative/nonfunctional, do not imply active behavior in future UI.
- Truncated dashboard labels use ellipsis; full meaning should remain available through a title, tooltip, or details view.
- Modal bodies scroll instead of growing beyond 85–88vh.
- Touch targets should be at least 44 × 44px. Existing 28–40px icon controls are implementation exceptions and should not be copied into new touch-first UI.
- Web buttons and custom SVG controls need visible :focus-visible treatment. Current CSS primarily defines focus for inputs.
- Custom Flutter GestureDetector controls need an explicit pressed, selected, or disabled state because they do not receive Material feedback automatically.
- The dashboard’s <=768px map-only layout removes operational panels rather than reflowing them; any new mobile dashboard work should provide an alternative drawer/sheet before treating that breakpoint as feature-complete.
- Dashboard modal shells currently lack a focus trap, Escape-key contract, explicit dialog semantics, and reliable initial focus.
- The autoplay background video and infinite status animations currently have no reduced-motion fallback.

Approximate contrast of core solid-color pairs:

| Pair | Ratio | Design implication |
|---|---:|---|
| #0F69C9 on #FFFFFF | 5.41:1 | Suitable for normal text |
| #0958A6 on #FFFFFF | 7.10:1 | Suitable for high-contrast headings |
| #38BDF8 on #FFFFFF | 2.14:1 | Accent only; not normal text on white |
| #94A3B8 on #F4F8FA | 2.40:1 | Too faint for essential copy |
| #CBD5E1 on #F4F8FA | 1.39:1 | Decorative/divider use only |
| #64748B on #1E293B | 3.07:1 | Too faint for normal dark-theme body copy |
| #FFFFFF on #7B93B0 | 3.16:1 | Legacy secondary button needs contrast review |

Glass, video, and map backgrounds change effective contrast, so rendered-state verification remains required.

## 14. Known visual inconsistencies

These are documented facts, not new design variants:

- Inter is named first on the dashboard but is never loaded.
- Flutter repeats colors, typography, radii, and card styles inline rather than consuming shared tokens.
- The dashboard uses #22C55E for generated vessel markers while the legend also uses #38BDF8.
- Success has three common greens (#2ECC71, #22C55E, #10B981); danger has three common reds (#E74C3C, #EF4444, #DC2626).
- Auth web primary is #1565C0 while the active product primary is #0F69C9.
- Admin setup is visually isolated from all other web pages.
- Flutter breakpoints use 600, 800, 900, and available width 550; web uses 480, 640, 700, 768, 860, 1024, and 1100.
- Web dashboard type is very dense (often 9–12px), while profile and Flutter body text are 14–16px.
- Light/dark state persists on web but not in Flutter.
- Theme-dependent hover backgrounds sometimes use white alpha even in light mode, reducing visible feedback.
- No frontend surface defines a reduced-motion mode.
- No universal web button-disabled style or focus-visible system exists.
- Auth mobile CSS tries to compact .card, while the actual component is .content-card, so that intended rule does not apply.
- The 80px landing raster logo is enlarged to 350px and may appear soft.
- Dashboard/profile generated content contains hard-coded white/dark tooltip colors that do not reliably adapt to both themes.
- The profile page repeats form IDs in different tab regions, weakening label association and creating a misleading security-tab presentation.
- Flutter PWA portrait locking conflicts with its desktop-responsive layouts.
- Venture uses light OpenStreetMap tiles in dark mode without a dark basemap or filter.
- Dashboard and Advisories Flutter destinations exist as visual screens but are disabled in the primary Home navigation stack.
- Advisory metadata and some compact Flutter headers can overflow on narrow screens.

When standardizing, preserve brand identity and semantic meaning first; then consolidate duplicate literals into the canonical token names.

## 15. Source map

Primary visual sources reviewed:

| Source | Responsibility |
|---|---|
| mobile/lib/main.dart | Flutter app root, login, legal/detail presentation |
| mobile/lib/createAccount.dart | Multi-step registration presentation |
| mobile/lib/home.dart | Responsive shell, home cards, navigation, profile editor |
| mobile/lib/venture.dart | Full-screen map, floating actions, checklists, SOS visuals |
| mobile/lib/dashboard.dart | Fisher analytics presentation |
| mobile/lib/advisories.dart | Advisory list/card presentation |
| mobile/lib/settings.dart | Theme switch, settings cards, information views |
| mobile/pubspec.yaml | Runtime assets and Material icon enablement |
| web/css/dashboard.css | Dashboard tokens, reset, layout, components, themes, motion |
| web/css/profile.css | Regulator profile layout and components |
| web/css/style.css | Landing/login visual system |
| web/css/terms.css | Terms layout and typography |
| web/html/dashboard.html | Dashboard composition and inline SVG/icon colors |
| web/html/dashboardprof.html | Profile composition |
| web/html/admin-signup.html | Isolated setup-form visual system |
| web/index.html, web/html/login.html, web/html/terms.html | Auth and policy composition |
| web/js/dashboard.js | Visual state classes, generated marker/pin palettes, theme behavior |
| web/js/jss.js | Profile tab/theme/toast visual state |
| mobile/assets and web/assets | Image, icon, video, and reference inventory |

Files concerned only with transport, configuration, models, session state, or nonvisual service behavior are outside this document’s scope.

## 16. Maintenance checklist

Before merging a frontend visual change:

- Use the canonical brand, surface, text, border, and semantic values.
- Test light and dark themes where the surface supports both.
- Verify Flutter below and above 900px; verify Venture around 800px.
- Verify web at 1100, 1024, 860, 768, 640, and 480px as applicable.
- Keep body text readable and reserve sub-12px sizes for operational metadata.
- Keep touch targets at least 44px and provide keyboard focus on web.
- Pair every semantic color with text/icon meaning.
- Use 12px dashboard or 16px mobile-card radius unless a documented component requires another value.
- Use 150–200ms ease for ordinary interaction motion.
- Ensure imagery uses contain for logos and cover for photos/backgrounds.
- Update this document when introducing or intentionally changing a token, breakpoint, reusable component, asset rule, or theme behavior.
