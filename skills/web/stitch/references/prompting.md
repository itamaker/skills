# Stitch Prompting Reference

This reference condenses the parts of the official Stitch docs that matter most when you are writing prompts or choosing how to generate.

## Starting a project

- Start broad when the user is still defining the product.
- Add detail once the concept is stable.
- Adjectives are useful because Stitch uses them to infer palette, typography, and imagery direction.
- For larger apps, refine screen by screen instead of trying to perfect the whole product in one prompt.

### Good starting shape

- `Idea`: what the product does and who it serves
- `Theme`: adjectives, palette direction, mood, and typography cues
- `Content`: core sections, entities, or flows that must appear
- `Navigation`: key screens, tabs, or top-level routes

### Better edit prompts

- Target one screen or component.
- Ask for one or two changes per prompt.
- Specify both `what` changes and `how` it should look afterward.
- Use explicit UI terms such as `hero`, `card`, `navigation bar`, `primary CTA`, `input`, or `episode list`.

## Theme and imagery controls

- Ask for exact colors when they are known.
- Ask for a mood when the palette should stay flexible.
- Call out font direction explicitly if it matters.
- If changing images, identify the exact screen and the content of the image you want changed.
- If changing theme colors, say whether images or icons should also be updated to match.
- If the user wants another language, ask Stitch to switch all copy and button text together.

## Device types

Choose device type based on the primary design surface, not just the viewport:

- `App`: vertical scroll, bottom-aligned or thumb-friendly navigation, stacked content.
- `Web`: top navigation, multi-column grids, wider hero treatments, more horizontal density.

When translating between device types:

- Prefer translation over raw resizing.
- Tell Stitch what should happen to navigation, hero structure, and grid density.
- If moving from App to Web inside the same project, switch the preview device type and be ready to manually expand the frame height so hidden content becomes visible.

## Design modes

- `Thinking with 3 Pro`: best for logic-heavy dashboards, complex information hierarchy, and production candidates.
- `Redesign (Nano Banana Pro)`: best for strong aesthetic restyling or vibe-driven experiments.
- `2.5 Pro`: best for high-fidelity HTML output and comparing alternate high-quality interpretations.
- `Fast`: best for quick wireframes and exports that will be refined elsewhere, especially in Figma.

## Variations

Use variations when:

- The current design is not working but the next move is unclear.
- The user wants multiple layout directions at once.
- The user wants a strong aesthetic pivot.

Do not use variations for tiny surgical changes. Use standard edit prompts for those.

When prompting for variations:

- Give a clear direction such as `minimal`, `editorial`, `luxury`, or `bold`.
- Combine layout and theme changes if the goal is exploration.
- Be explicit about the screen you want varied.
- After choosing a winner, iterate on that winner with a narrower follow-up.

## Working heuristics

- Start broad, then refine.
- One focused edit beats one overloaded edit.
- Translate across devices; do not simply squeeze or stretch.
- Use variations for exploration and regular edits for control.
