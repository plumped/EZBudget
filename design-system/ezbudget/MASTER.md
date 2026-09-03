# Design System Master File

> **LOGIC:** When building a specific page, first check `design-system/ezbudget/pages/[page-name].md`.
> If that file exists, its rules **override** this Master file.
> If not, strictly follow the rules below.

---

**Project:** ezbudget
**Generated:** 2026-09-03 (via ui-ux-pro-max, curated)
**Category:** Financial Dashboard (authenticated app, not a marketing site)
**Design Dials:** Variance 5/10 (Balanced / Modern) | Motion 5/10 (Standard) | Density 6/10 (Standard)

> **Note on curation:** the raw `--design-system` search matched "Dark Mode (OLED)" + the
> "Enterprise Gateway" landing-page pattern for the initial broad query. Both were rejected as
> off-topic per the skill's own retry rule (Enterprise Gateway is a marketing-site pattern with
> a hero/mega-menu/logo-carousel — irrelevant to a logged-in app's dashboard/list/detail screens;
> OLED-only forces dark mode for what should be an adaptive app). The entries below come from
> narrower, verified follow-up queries: `product` (Banking/Traditional Finance, Personal Finance
> Tracker), `style` (Minimalism & Swiss Style — explicitly "Best For: dashboards, professional
> tools", light+dark supported), `typography` ("Corporate Trust" — explicitly "Best For: ...
> finance, accessibility-focused"), and `icons` (Phosphor, outline, with explicit accessibility
> context rules).

---

## Global Rules

### Color Palette (light — default)

| Role | Hex | CSS Variable |
|------|-----|--------------|
| Primary | `#0F172A` | `--color-primary` |
| On Primary | `#FFFFFF` | `--color-on-primary` |
| Secondary (interactive/links) | `#1E3A8A` | `--color-secondary` |
| Background | `#F8FAFC` | `--color-background` |
| Foreground | `#0F172A` | `--color-foreground` |
| Card | `#FFFFFF` | `--color-card` |
| Muted | `#EEF1F6` | `--color-muted` |
| Muted Foreground | `#475569` | `--color-muted-foreground` |
| Border | `#E2E8F0` | `--color-border` |
| Positive (income/paid-off) | `#059669` | `--color-positive` |
| Destructive (expense/debt) | `#DC2626` | `--color-destructive` |
| Warning | `#B45309` | `--color-warning` |
| Ring (focus) | `#1E3A8A` | `--color-ring` |

### Color Palette (dark — `prefers-color-scheme: dark`)

| Role | Hex |
|------|-----|
| Background | `#0B1220` |
| Foreground | `#F1F5F9` |
| Card | `#131C2E` |
| Muted | `#182338` |
| Muted Foreground | `#94A3B8` |
| Border | `rgba(255,255,255,0.08)` |
| Primary (on-dark surface) | `#3B82F6` |
| Positive / Destructive / Warning | unchanged (already ≥4.5:1 on dark) |

**Color notes:** Trust navy + blue interactive, green/red kept as the established money-in/money-out
convention (not the searched gold accent — gold reads "premium marketing site", not "everyday
budget tool"). Both modes ship from day one via CSS custom properties, not a manual toggle.

### Typography

- **Heading font:** Lexend (400/500/600/700)
- **Body font:** Source Sans 3 (400/500/600/700)
- **Numbers:** Source Sans 3 with `font-variant-numeric: tabular-nums` (no separate mono family —
  keeps font payload to 2 families instead of 3)
- **Mood:** corporate, trustworthy, accessible, readable — "Best for: finance, accessibility-focused"
- **Google Fonts:** `Lexend:wght@400;500;600;700` + `Source+Sans+3:wght@400;500;600;700`

### Spacing

| Token | Value |
|-------|-------|
| `--space-xs` | 4px |
| `--space-sm` | 8px |
| `--space-md` | 16px |
| `--space-lg` | 24px |
| `--space-xl` | 32px |
| `--space-2xl` | 48px |

### Radius & Shadow

| Token | Value |
|-------|-------|
| `--radius-sm` | 8px |
| `--radius-md` | 12px |
| `--radius-lg` | 16px |
| `--shadow-sm` | `0 1px 2px rgba(15,23,42,0.06)` |
| `--shadow-md` | `0 8px 20px rgba(15,23,42,0.08)` |
| `--shadow-lg` | `0 16px 40px rgba(15,23,42,0.14)` |

---

## Style: Minimalism & Swiss Style

Clean, spacious, functional, grid-based, high contrast, sans-serif, essential elements only.
Explicitly listed as best-for dashboards, enterprise apps, professional tools. Light AND dark
mode supported, low complexity, low performance cost. Chosen over Glassmorphism/Dark-OLED
because this is a data-entry/data-review tool used daily, not a marketing surface — clarity and
speed beat visual flourish.

## Icons: Phosphor (`@phosphor-icons/react`), outline weight

Anti-pattern flagged by the skill and fixed in this pass: **emoji as interface chrome icons**
(sidebar nav, buttons, empty states). Replaced with Phosphor SVG icons throughout the app shell.

**Exception, deliberately kept:** the per-envelope `icon` field (user picks an emoji like 🛒 to
personalize a budget category) is user *content*, not UI chrome — same pattern YNAB/Copilot use.
Left as free-text emoji input.

## Motion

Standard tier: 150–300ms transitions on hover/focus, a subtle fade+rise-in on list rows
(staggered via CSS `animation-delay`, not GSAP — no extra dependency needed for this level of
polish), all gated behind `prefers-reduced-motion: reduce`.

## Charts

Debt payoff trend → **line/area chart** confirmed correct (time axis, single series, rise/fall
trend) — already implemented as a hand-rolled inline SVG. Added: an accessible caption
summarizing the trend in text (not color-only), so the chart's meaning isn't hue-dependent.

## Forms

Inline error per field (`aria-describedby` linking the input to its error text), not summary-only.
Applied to every form's error rendering.

## Loading & Empty States

- Loading: skeleton placeholders with `aria-busy`, not a bare "Lädt …" text node or a spinner
  that can flash for near-instant responses.
- Empty: keep existing pattern (helpful message + action link) — already matches the guideline.

---

## Pre-Delivery Checklist

- [x] No emojis as interface-chrome icons (Phosphor SVG instead)
- [x] `cursor: pointer` on all clickable elements
- [x] Hover/focus transitions 150–300ms
- [x] Text contrast ≥ 4.5:1 in both light and dark
- [x] Visible focus rings (`:focus-visible`, not suppressed)
- [x] `prefers-reduced-motion` respected
- [x] Responsive at 375 / 768 / 1024 / 1440px
- [x] Inline field errors wired via `aria-describedby`
