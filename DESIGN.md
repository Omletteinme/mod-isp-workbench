---
name: MOD-ISP Workbench
description: A local image-restoration workbench for comparing processing paths and measured outputs.
colors:
  ink: "#17191e"
  night: "#111318"
  canvas: "#ffffff"
  accent: "#2056ed"
  accent-dark: "#1743c3"
  accent-wash: "#eff3ff"
  line: "#e5e6e8"
  muted: "#62666d"
typography:
  display:
    fontFamily: "Manrope, sans-serif"
    fontSize: "clamp(34px, 4.3vw, 56px)"
    fontWeight: 600
    lineHeight: 1.06
    letterSpacing: "-0.055em"
  body:
    fontFamily: "Manrope, sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "DM Mono, monospace"
    fontSize: "9px"
    fontWeight: 400
    letterSpacing: "0.08em"
rounded:
  sharp: "1px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "24px"
  xl: "32px"
components:
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.canvas}"
    typography: "Manrope, 11px, 700"
    rounded: "{rounded.sharp}"
    padding: "0 13px"
    height: "42px"
---

# Design System: MOD-ISP Workbench

## Overview

**Creative North Star: The Image Signal Workbench**

The interface treats restoration as a hands-on investigation. A dark signal field introduces the image pipeline; a white, finely ruled work surface keeps image evidence and measured outputs legible. Cobalt marks the active route and important actions. Compact mono labels identify technical context without turning the whole interface into a console.

The user-provided reference informs the grid, contrast, cobalt signal pattern, and editorial typography. The app remains a working tool: no invented customers, demo metrics, or claims of general quality.

**Key Characteristics:**
- Real image comparisons take visual priority.
- One cobalt accent marks active controls and route state.
- Hairline rules create structure; surfaces remain mostly flat.
- Motion confirms processing and result changes, with reduced-motion support.

## Colors

The palette pairs near-black instrument framing and white work surfaces with a single saturated cobalt accent.

### Primary
- **Signal Cobalt** (#2056ed): Active route, primary action, links, and small signal marks.
- **Deep Cobalt** (#1743c3): Hover and pressed states.

### Neutral
- **Instrument Ink** (#17191e): Primary text.
- **Night Field** (#111318): Header and signal panel.
- **White Ground** (#ffffff): Main work surface.
- **Rule Gray** (#e5e6e8): Dividers and image plate borders.
- **Slate Text** (#62666d): Supporting text.

## Typography

**Display Font:** Manrope (self-hosted, variable)
**Body Font:** Manrope (self-hosted)
**Label/Mono Font:** DM Mono (self-hosted)

**Character:** Manrope carries compact, confident headings and readable controls. DM Mono is reserved for measured values, technical labels, dimensions, and status.

### Hierarchy
- **Display** (600, 34–56px, 1.06): Workbench statement.
- **Title** (650, 19–21px, 1.2): Workflow section headings.
- **Body** (400, 11–14px, 1.5): Explanations and control labels.
- **Label** (400, 8–10px, 1.4, mono): Data labels and indices; keep readable and high-contrast.

Manrope and DM Mono are licensed under the SIL Open Font License; license texts are in `static/fonts/`.

## Layout

The desktop work surface is capped at 1320px with 30px gutters. It flows in task order: input and profile, paired source/output plates, processing paths, then measurements. The comparison is the largest light-surface region. At narrow widths the input row spans the control strip, the two image plates stack, and the measurement table scrolls horizontally rather than collapsing values.

## Elevation & Depth

The system is flat. Borders, dark/light field changes, and selection fills establish hierarchy. A restrained neutral shadow is reserved for the open adjustments panel; avoid colored glows and persistent elevation.

## Shapes

Use square or 1px corners. Image plates, controls, and rows use 1px rules. Keep the geometry precise and avoid pill-shaped containers.

## Components

### Primary action
A cobalt rectangular button with an explicit verb, a concise arrow, visible disabled state, and short hover transition. While processing, the action label changes and its glyph rotates.

### Image plates
Each plate has a compact caption with source/output role and actual file or dimension metadata. Empty state uses a quiet registration grid; loaded images are contained rather than cropped.

### Processing path rows
Use full-width selectable rows. Show the method, domain-specific description, actual runtime, availability/routing state, and a quiet selected tint. Disabled paths remain legible.

### Measurements
Use tabular numerals and aligned columns. Distinguish run-local memory from reference quality; explain when reference metrics are unavailable.

## Do's and Don'ts

- Do keep rendered RGB and Bayer sensor inputs distinct in descriptions.
- Do show that processing runs locally and that the implementation is experimental.
- Do label measured values with their actual scope and caveats.
- Don't add testimonials, unsupported benchmark claims, or fabricated images.
- Don't animate full-resolution image pixels or introduce motion that delays a task.
- Don't use cobalt glow, decorative gradients, or generic rounded cards.
