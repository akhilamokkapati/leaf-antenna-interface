---
name: Instrument Teal
colors:
  bg: "#F3F6F7"
  surface: "#FFFFFF"
  surface-sunken: "#F8FAFB"
  ink: "#0D1B2A"
  ink-soft: "#31445C"
  muted: "#6A7C92"
  faint: "#9AA8BA"
  line: "#E7ECF1"
  line-soft: "#EFF3F6"
  teal: "#0F766E"
  teal-bright: "#13A394"
  teal-deep: "#0B5C55"
  teal-wash: "#E5F4F1"
  sidebar-top: "#12857B"
  sidebar-bottom: "#0B4F49"
  pass: "#15803D"
  pass-wash: "#DCFCE7"
  fail: "#B91C1C"
  fail-wash: "#FEE2E2"
typography:
  display:
    fontFamily: Segoe UI
    fontSize: 24px
    fontWeight: "800"
    letterSpacing: "-0.025em"
  section-label:
    fontFamily: Segoe UI
    fontSize: 11.5px
    fontWeight: "700"
    letterSpacing: "0.1em"
  metric:
    fontFamily: Segoe UI
    fontSize: 27px
    fontWeight: "800"
    letterSpacing: "-0.03em"
  body:
    fontFamily: Segoe UI
    fontSize: 14px
    fontWeight: "400"
    lineHeight: 1.5
rounded:
  sm: 8px
  md: 12px
  lg: 16px
spacing:
  xs: 6px
  sm: 10px
  md: 18px
  lg: 28px
---

## Overview

The clean control software of a modern benchtop RF instrument. Calm, precise,
and legible under lab lighting -- the kind of screen an engineer stares at for
hours without fatigue. The audience is an engineer and their professor reading
measured antenna data, so the interface is quiet and data-forward: it reports,
it does not sell.

A single teal, used as a branded gradient, carries the identity and every
interaction. Everything else is cool neutrals so the measured signal and the
readings are what draw the eye.

## Colors

A cool, high-legibility neutral system with one teal accent (used as a subtle
top-to-bottom gradient for brand surfaces).

- **Background** {colors.bg} is a cool off-white lab surface; **surface** {colors.surface} is the white a card sits on.
- **Ink** {colors.ink} is a deep cool navy-black for headings and core text; **muted** {colors.muted} and **faint** {colors.faint} carry captions, metadata, and axis labels.
- **Line** {colors.line} is a cool hairline for borders and dividers.
- **Teal** {colors.teal} (with {colors.teal-bright} and {colors.teal-deep}) is the single accent and brand color: the sidebar gradient ({colors.sidebar-top} to {colors.sidebar-bottom}), the measured S11 trace, primary buttons, and the accent bar on a metric card. Interaction and brand only.
- **Pass** {colors.pass} marks a good result state ("covers the WiFi band", on-target frequency); **Fail** {colors.fail} marks a failing one. These appear only as result badges, never as chrome.

## Typography

A clean sans (system UI / Segoe UI) throughout, tuned by weight and tracking
rather than by adding typefaces. All numerals are tabular so measured values sit
in tidy, non-jittering columns as they update.

- **Display** {typography.display} -- the page title, set once, tight tracking.
- **Section label** {typography.section-label} -- uppercase, wide tracking, muted; titles each card and sidebar group.
- **Metric** {typography.metric} -- large tabular figures for the three headline readings.
- **Body** {typography.body} -- everything else.

## Layout & Components

- A fixed **branded teal sidebar** (subtle vertical gradient) holds the parameter controls and anchors the identity.
- The content area is a cool light canvas with white **cards**: hairline border, soft layered shadow, {rounded.lg} corners.
- **Metric cards** carry a thin teal-gradient accent bar across the top, an uppercase label, one large tabular figure, and a one-word caption.
- Spacing is generous, on an ~8px rhythm; the layout is centered with a comfortable max width.

## Data & Charts

The S11 plot is the focal figure: a boxed plot frame, cool hairline grid, muted
axis labels, the measured trace in teal with a soft wash beneath it, and a marker
+ label at resonance. The WiFi band is a pale teal-wash column; the -10 dB and
2.45 GHz guides are thin dashed rules; previous runs are faint gray for
comparison and never compete with the current trace.

## Do's and Don'ts

- **Do** keep neutrals cool and let the teal and the data draw the eye.
- **Do** keep all figures tabular and aligned so a row of metrics reads as calm data.
- **Don't** introduce a second accent color; teal is the only brand/interactive color.
- **Don't** color captions, metadata, or axis labels -- those stay muted.
- **Don't** pile on heavy shadows or decorative gradients beyond the branded teal surfaces.
