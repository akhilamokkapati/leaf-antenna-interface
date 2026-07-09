---
name: Herbarium Instrument
colors:
  paper: "#F1EEE5"
  surface: "#FBFAF4"
  surface-sunken: "#F4F1E7"
  ink: "#17211E"
  ink-soft: "#2E3A36"
  muted: "#6E7A72"
  faint: "#9AA39B"
  line: "#E3DECF"
  line-soft: "#EDE8DB"
  teal: "#0C5F57"
  teal-bright: "#12897E"
  teal-deep: "#0A4A44"
  teal-wash: "#DCEBE7"
  grow: "#2E6B43"
  grow-wash: "#DDEAD9"
  clay: "#A6432A"
  clay-wash: "#F0DCCF"
typography:
  display:
    fontFamily: Inter
    fontSize: 26px
    fontWeight: "800"
    letterSpacing: "-0.02em"
  section-label:
    fontFamily: Space Grotesk
    fontSize: 11px
    fontWeight: "600"
    letterSpacing: "0.13em"
  body:
    fontFamily: Inter
    fontSize: 13.5px
    fontWeight: "400"
    lineHeight: 1.5
  metric:
    fontFamily: Inter
    fontSize: 28px
    fontWeight: "800"
    letterSpacing: "-0.03em"
rounded:
  sm: 8px
  md: 12px
  lg: 16px
spacing:
  xs: 6px
  sm: 10px
  md: 16px
  lg: 24px
---

## Overview

A precision benchtop RF instrument's display, reimagined as a botanical
herbarium plate. It should feel like a scientific field guide printed on warm
paper: exact, calm, and unhurried. The audience is an engineer and their
professor reading measured data, not a shopper being sold to. Every screen does
work; nothing performs.

The leaf is the subject of study, so it is honored the way a herbarium honors a
specimen: through precise linework, generous margins, and a single ink -- never
through decoration. The one accent, a patinated copper-teal, behaves like the
oxidized-green ink of an old botanical plate. It carries interaction and the
measured signal, and nothing else.

## Colors

A warm-paper, single-ink-plus-accent system. The neutrals are warm (limestone,
never cool gray or pure white); the accent is one patinated teal.

- **Paper** {colors.paper} is the canvas -- warmed limestone stock, never pure white.
- **Surface** {colors.surface} is the raised plate a card sits on, a shade brighter than paper.
- **Ink** {colors.ink} is graphite-warm and carries all typography and hairline rules; never pure black.
- **Muted** {colors.muted} is a slate-sage for captions, metadata, axis labels.
- **Line** {colors.line} is a warm hairline for rules, borders, table dividers.
- **Teal** {colors.teal} is the single accent: the branded sidebar, the measured S11 trace, primary buttons, the value in a metric. Interaction only.
- **Grow** {colors.grow} (a botanical green) marks a *good* state: "covers the WiFi band", on-target frequency. Used sparingly, only for a passing result.
- **Clay** {colors.clay} (a botanical vermilion) marks a *failing* state only: "does not cover the band". Never used for chrome, metadata, or emphasis.

## Typography

Inter for everything readable; Space Grotesk for the small uppercase labels that
title each plate, like the printed captions on a herbarium sheet. All numerals
are tabular so measured values sit in tidy columns and never jitter as they
update.

- **Display** {typography.display} -- the page title. One size larger than anything else, tight tracking, set once.
- **Section label** {typography.section-label} -- uppercase, wide tracking, muted. Titles cards and sidebar groups. This is the herbarium plate caption.
- **Metric** {typography.metric} -- large tabular figures for the three headline readings; the ink color, not teal, so several read as a calm row.
- **Body** {typography.body} -- everything else.

## Layout & Components

- A fixed **teal sidebar** anchors the identity and holds the parameter controls. It is a deep, matte, near-flat teal -- an instrument's bezel, not a glossy gradient.
- The content area is warm paper with cards as **plates**: surface fill, a warm hairline border, and a whisper-soft shadow (barely there). Prefer the border to the shadow; this is print, not glassmorphism.
- **Metric cards** are quiet: a small uppercase label, one large tabular figure in ink, a one-word caption. A single 2px teal tick sits at the top-left corner as a registration mark -- not a full gradient bar.
- Corners are lightly rounded ({rounded.md}); spacing is generous and on an 8px rhythm.

## Data & Charts

The S11 plot is a **scientific figure**, not a dashboard widget. Warm hairline
grid, a boxed plot frame, muted axis labels, the measured trace in teal with a
soft wash beneath it, and a small marker + label at resonance. It carries a
figure caption beneath it. The WiFi band is a pale teal-wash column; the -10 dB
and 2.45 GHz guides are thin dashed rules. Previous runs are faint gray, for
comparison, never competing with the current trace.

## Do's and Don'ts

- **Do** use warm hairline rules and generous margins to separate content. Let whitespace do the work.
- **Do** keep all figures tabular and in ink; a row of metrics should read as calm, aligned data.
- **Don't** use glows, heavy drop shadows, or gradients as decoration. A card is a printed plate, not a floating pane.
- **Don't** introduce a second accent. Teal is the only interactive/brand color; grow and clay appear *only* as result states (pass/fail), never as chrome.
- **Don't** color metadata, captions, or axis labels -- those are always muted, never teal.
- **Don't** add rounded-blob illustration or emoji flourish. The leaf appears only as precise linework in the geometry plate.
