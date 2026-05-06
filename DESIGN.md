# Sprecher DESIGN.md

## Color Strategy: Restrained

Deep dark background with subtle surface elevation. One accent (purple) used sparingly for primary actions. Teal for status/success. No high-chroma neons.

## Scene

Human operator at desk in a dimly-lit room, running Sprecher on their local server. Checking job status, managing voices. Late evening, focused work. Ambient light is low. Mood: calm, capable, in control.

→ **Dark theme is correct here.** Low ambient light, focused task, operator in control.

## Palette

```css
:root {
  /* Backgrounds - deep dark, slightly warm-tinted */
  --sp-bg: #0c0c0f;           /* Main background */
  --sp-surface: #141419;       /* Cards, panels */
  --sp-surface-hover: #1a1a21; /* Hover states */
  --sp-surface-raised: #1e1e26; /* Elevated elements */

  /* Borders */
  --sp-border: #2a2a35;       /* Subtle borders */
  --sp-border-focus: #3d3d4d; /* Focus rings */

  /* Text */
  --sp-text: #e8e8ed;          /* Primary text */
  --sp-text-secondary: #a8a8b8; /* Secondary text */
  --sp-muted: #6868a0;         /* Muted/placeholder */

  /* Accents */
  --sp-accent: #7c5cfc;        /* Purple - primary actions */
  --sp-accent-hover: #9174fd;  /* Purple hover */
  --sp-accent-muted: #7c5cfc1a; /* Purple tint for backgrounds */

  --sp-accent2: #00d4aa;       /* Teal - status, success */
  --sp-accent2-muted: #00d4aa1a; /* Teal tint */

  /* Semantic */
  --sp-danger: #ff5c5c;
  --sp-warning: #ffc107;
  --sp-success: #22c55e;
}
```

## Typography

**Font:** System UI stack for performance (no web font loading).
```css
font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
```

**Scale:** 14px base. Headings use weight contrast, not just size.
- `text-sm`: 12px
- `text-base`: 14px
- `text-lg`: 16px
- `text-xl`: 18px
- `text-2xl`: 20px
- `text-3xl`: 24px

**Line length:** 65-75ch max for body text.

## Elevation

Surfaces differ by background color, not shadows alone:
- Base: `--sp-bg`
- Card: `--sp-surface` with 1px `--sp-border`
- Elevated: `--sp-surface-raised` with subtle border
- No drop shadows (feels dated)

## Component Patterns

### Cards
- Background: `--sp-surface`
- Border: 1px `--sp-border`
- Border-radius: 8px
- Padding: 16px (compact) or 24px (spacious)
- No shadows

### Buttons
- **Primary:** `--sp-accent` background, white text, hover `--sp-accent-hover`
- **Secondary:** `--sp-surface` background, `--sp-border` border, `--sp-text` color
- **Ghost:** transparent, `--sp-text`, hover `--sp-surface-hover`
- Border-radius: 6px, padding: 8px 16px
- No shadows, no gradients

### Status Badges
- **Running:** Teal (`--sp-accent2`) text + subtle teal background tint
- **Completed:** Green (`--sp-success`) 
- **Failed:** Red (`--sp-danger`)
- **Queued:** Yellow (`--sp-warning`)
- Small dot + text, 12px font, uppercase tracking

### Form Inputs
- Background: `--sp-surface`
- Border: 1px `--sp-border`, focus: `--sp-border-focus` + `--sp-accent`
- Border-radius: 6px
- Placeholder: `--sp-muted`

### Navigation
- Sidebar: fixed left, `--sp-surface` background, 240px wide
- Nav items: 40px tall, full-width, `--sp-text-secondary` default, `--sp-text` + `--sp-accent-muted` background on active/hover
- Icons: 20px, Boxicons, `--sp-muted` default

## Motion

- Duration: 150ms for micro-interactions, 250ms for page transitions
- Easing: `cubic-bezier(0.25, 0.1, 0.25, 1)` (ease-out-quart feel)
- Animate: opacity, transform, color. Never layout properties.
- Pulse dot animation for running status: subtle, 2s infinite

## Anti-patterns to Avoid

- **No glassmorphism** — not decorative, this isn't that aesthetic
- **No gradient text** — solid colors only
- **No side-stripe borders** — full borders or nothing
- **No card grids with identical content** — vary sizes, use real hierarchy
- **No modal-first** — inline forms, progressive disclosure

## Layout Rhythm

- Sidebar: 240px fixed
- Main content: fluid, max-width 1200px
- Page padding: 32px
- Card spacing: 16px gap in grids
- Section spacing: 48px between major sections
