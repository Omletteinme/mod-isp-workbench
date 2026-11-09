---
name: Photosite Workbench
description: A local image-restoration workbench for comparing processing paths and measured outputs, presented as a bento board of flat tiles.
colors:
  page: "#0b0b0d"
  tile: "#f1f1f3"
  ink: "#0d0d10"
  violet: "#7357f6"
  violet-deep: "#5a3ff0"
  lavender: "#dcd5ff"
  peach: "#f6efe9"
  orange: "#f47a3a"
  yellow: "#f5d13b"
  muted: "#5d5f66"
  line: "#d9d9de"
typography:
  display:
    fontFamily: "Manrope, sans-serif"
    fontSize: "clamp(24px, 2.3vw, 34px)"
    fontWeight: 600
    lineHeight: 1.08
    letterSpacing: "-0.045em"
  wordmark:
    fontFamily: "Manrope, sans-serif"
    fontWeight: 700
    letterSpacing: "-0.06em"
    note: "Always lowercase: photosite"
  body:
    fontFamily: "Manrope, sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "DM Mono, monospace"
    fontSize: "10px"
    letterSpacing: "0.08em"
rounded:
  tile: "8px"
  pill: "999px"
spacing:
  gap: "10px"
  tile-padding: "28px"
components:
  pill-primary:
    backgroundColor: "{colors.violet-deep}"
    textColor: "#ffffff"
    rounded: "{rounded.pill}"
    height: "46px"
  pill-outline:
    border: "1.5px solid {colors.ink}"
    rounded: "{rounded.pill}"
---

# Design System: Photosite Workbench

## Overview

**Creative North Star: A Board of Flat Tiles**

The page is a near-black field holding tiles with 10px gaps and 8px corners. Each tile is one flat surface: solid violet, off-white, lavender gradient, peach-to-orange gradient, or black. Tiles do not nest inside other tiles. Hairline dividers separate things inside a tile.

The hero is a bento grid. A tall poster tile holds the headline over a grey dot field and an animated 3D Bayer mosaic (RGGB photosites on a silicon plate) rendered as violet halftone. The other tiles carry the mark, the lowercase wordmark, a halftone aperture, a tagline and format glyphs, and capability pills. Below the hero, the workbench sections reuse the same tile surfaces. The comparison panels sit directly on the dark page.

The look takes its structure (bento grid, halftone art, pill tags, outlined and filled dot clusters) from a brand board supplied by the project owner. It uses Photosite's own name, mark and copy. The app remains a working tool: no invented customers, demo metrics, or claims of general quality.

**Key Characteristics:**
- Flat tiles on near-black, never boxes in boxes.
- Violet is the signal colour; orange and yellow appear only in pills and the gradient tile.
- Pills (999px radius) carry state and capability labels: black for classical, violet for learned, burnt orange for hybrid.
- Mono labels at 9–10px for metadata only; Manrope for everything else.
- Real image comparisons take visual priority.

## Colors

- **Page** (`#0b0b0d`) is the background behind every tile.
- **Tile** (`#f1f1f3`) is the working surface for forms, tables and paths.
- **Violet** (`#7357f6`) fills the logo tile and halftone art; **Violet deep** (`#5a3ff0`) is for buttons, active states and small coloured text, because white on it passes contrast.
- **Lavender**, **peach** and **orange** appear in the measurements tile, the capability tile and the large mark tile.
- **Muted** (`#5d5f66`) is secondary text on off-white tiles.

## Typography

Manrope (self-hosted variable font) at weight 600–800 for headings, with tight negative tracking. DM Mono (self-hosted) for corner labels, section indexes and metric labels. Section headings are sentence case; taglines inside tiles are uppercase and medium weight.

## Components

- **Pills:** primary (violet-deep fill), white, outlined, black and yellow variants. Used for the CTA, nav, privacy note, capability tags and path states.
- **Controls:** the source-image, profile, reference and adjustments controls sit in one row divided by hairlines. The segmented profile control is a pill with a black active state.
- **Before/after slider:** one black tile holds the source (left) and the processed output (right) stacked in a single frame, with a draggable violet handle. Click or drag anywhere on the image, or use the arrow keys, Home and End on the handle (Shift for bigger steps). Empty states show a dot field with one message on each side of the handle.
- **Pipeline figure:** the "How it works" tile sits on `#15131c` with the steps on the left and an isometric react-isokit figure on the right, themed with the violet palette (orange when the classical path is taken). Source is `web/src/components/ui/isp-pipeline.tsx` and `.css`; `web/build.mjs` bundles it into `static/pipeline.js` and `static/pipeline.css`.
- **Mosaic:** `static/mosaic.js` draws the poster artwork with WebGL2. It falls back to the static dot field without WebGL2 and draws one still frame under `prefers-reduced-motion`.

## Layout

The hero is a 12-column, 6-row grid sized to `clamp(560px, 100vh − 100px, 780px)` so the headline, call to action and mosaic are visible on a small laptop. It is staggered: the poster spans rows 1–5, the logo tile rows 1–2, the wordmark rows 1–3, the aperture tile rows 3–6, the capability pills rows 4–6, and the tagline row 6, so no two columns split at the same row. Below the hero, sections sit one or two columns off each other (setup and RAW record at columns 1–11, the workflow tile at 2–12, processing paths at 1–10, measurements at 3–12). At 1040px and below everything is full width and the offsets drop; at 700px and below the hero is one column and the logo tile is hidden.
