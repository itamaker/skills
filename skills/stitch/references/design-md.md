# DESIGN.md Reference

`DESIGN.md` is a plain-text design system document for agents. It plays the same role for visual consistency that `AGENTS.md` plays for engineering process.

## What it is for

Use `DESIGN.md` when the user needs multiple generated screens to share one visual language:

- consistent palette
- typography rules
- component styling
- spacing and elevation rules
- practical guardrails

Treat it as a living document. It should evolve with the design rather than freeze the first draft forever.

## Section order

Preserve this order when authoring or revising:

1. `Overview`
2. `Colors`
3. `Typography`
4. `Elevation`
5. `Components`
6. `Do's and Don'ts`

Sections can be omitted if they are genuinely irrelevant, but do not shuffle the order.

## Authoring rules

- `Overview`: describe the overall personality and operating constraints.
- `Colors`: name the major roles and explain what each color is for.
- `Typography`: explain font families, weights, and typical sizes.
- `Elevation`: say whether depth comes from shadows, borders, surface contrast, or a flat system.
- `Components`: focus on the components that matter most for the product.
- `Do's and Don'ts`: keep these concrete and enforceable.

When exact values are known, write them literally. When the user only knows the vibe, describe the intent clearly and let Stitch reconcile that into tokens.

## Starter template

```md
# Design System

## Overview
A calm, precise interface for a B2B analytics product.
Dense enough for expert users, but never visually noisy.

## Colors
- **Primary** (#1f5eff): Primary actions, selected states, key highlights
- **Secondary** (#5d6b8a): Supporting actions and lower-emphasis UI
- **Tertiary** (#14b8a6): Data accents, success-adjacent highlights, small callouts
- **Neutral** (#7b8498): Borders, surfaces, and non-brand structure

## Typography
- **Headline Font**: Inter
- **Body Font**: Inter
- **Label Font**: Inter

Headlines use semibold weight.
Body text uses regular weight at 14-16px.
Labels use medium weight with tighter tracking.

## Elevation
The system is mostly flat. Depth comes from border contrast and surface layering, not large shadows.

## Components
- **Buttons**: 10px radius, primary uses solid fill, secondary uses outline
- **Inputs**: 1px border, quiet surface fill, clear error states
- **Cards**: Subtle surface contrast, no heavy shadows, consistent header spacing
- **Tables**: Strong row alignment, restrained zebra striping, sticky header on dense views

## Do's and Don'ts
- Do reserve the primary color for the most important action on a screen
- Do keep spacing increments consistent across cards, forms, and tables
- Don't mix rounded and sharp corners in the same interface
- Don't use more than two font weights in one view unless the user explicitly asks for editorial contrast
```

## Working heuristics

- Keep it short enough to stay legible.
- Prefer role-based guidance over dumping raw tokens with no explanation.
- Add product-specific components when they matter, such as nav bars, data tables, or media cards.
- Revisit the document after major design pivots so future screens stay aligned.
