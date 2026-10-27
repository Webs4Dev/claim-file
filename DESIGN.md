---
name: ClaimFile
description: Calm, plain-language claims portal for accident claimants and the reviewers who decide them.
colors:
  harbour-teal: "#087f78"
  harbour-teal-dark: "#066c66"
  harbour-teal-darker: "#055a55"
  harbour-teal-bright: "#1fa58a"
  harbour-teal-soft: "#eaf6f4"
  harbour-teal-line: "#cfe7e3"
  harbour-teal-ring: "#d7eeeb"
  on-brand: "#e8f5f3"
  on-brand-muted: "#bfe3de"
  on-brand-accent: "#a8e3da"
  bg: "#f6f8fb"
  surface: "#ffffff"
  surface-subtle: "#f9fbfc"
  surface-muted: "#f4f7f9"
  surface-sunken: "#e2e9ef"
  line-soft: "#eff2f5"
  line: "#e7edf2"
  line-strong: "#d6dfe6"
  control-border: "#7f96ac"
  scrim: "rgba(23, 43, 66, 0.38)"
  text-strong: "#192e45"
  text: "#20334a"
  text-secondary: "#44586d"
  text-muted: "#637283"
  text-inverse: "#ffffff"
  success-fg: "#257e5b"
  success-bg: "#eef9f2"
  success-line: "#d3eddf"
  success-solid: "#2fa070"
  info-fg: "#476eb0"
  info-bg: "#f0f5ff"
  info-line: "#dce7fb"
  info-solid: "#5278b9"
  warning-fg: "#a15f2c"
  warning-bg: "#fff5ec"
  warning-line: "#f2dfcf"
  warning-solid: "#be8c2c"
  review-fg: "#735fba"
  review-bg: "#f4f1ff"
  review-line: "#e4ddfa"
  review-solid: "#8371c2"
  danger-fg: "#b74c4c"
  danger-bg: "#fff1f1"
  danger-line: "#f2d9d9"
  danger-solid: "#c95c5c"
typography:
  display:
    fontFamily: "Manrope, DM Sans, system-ui, sans-serif"
    fontSize: "30px"
    fontWeight: 800
  headline:
    fontFamily: "Manrope, DM Sans, system-ui, sans-serif"
    fontSize: "clamp(26px, 2.4vw, 32px)"
    fontWeight: 800
    lineHeight: 1.2
    letterSpacing: "-0.8px"
  title:
    fontFamily: "Manrope, DM Sans, system-ui, sans-serif"
    fontSize: "17px"
    fontWeight: 800
  body:
    fontFamily: "DM Sans, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 1.5
  body-dense:
    fontFamily: "DM Sans, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "DM Sans, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "12px"
    fontWeight: 600
    lineHeight: 1.4
rounded:
  sm: "6px"
  md: "10px"
  lg: "14px"
  pill: "999px"
spacing:
  "1": "4px"
  "2": "8px"
  "3": "12px"
  "4": "16px"
  "5": "20px"
  "6": "24px"
  "8": "32px"
  "10": "40px"
  "14": "56px"
components:
  button-primary:
    backgroundColor: "{colors.harbour-teal}"
    textColor: "{colors.text-inverse}"
    rounded: "{rounded.md}"
    padding: "0 18px"
    height: "42px"
  button-primary-hover:
    backgroundColor: "{colors.harbour-teal-dark}"
    textColor: "{colors.text-inverse}"
  button-secondary:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text-secondary}"
    rounded: "{rounded.md}"
    padding: "0 18px"
    height: "42px"
  button-secondary-hover:
    backgroundColor: "{colors.bg}"
  button-danger:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.danger-fg}"
    rounded: "{rounded.md}"
    padding: "0 18px"
    height: "42px"
  button-danger-hover:
    backgroundColor: "{colors.danger-bg}"
  button-small:
    rounded: "{rounded.md}"
    padding: "0 13px"
    height: "35px"
  status-badge-success:
    backgroundColor: "{colors.success-bg}"
    textColor: "{colors.success-fg}"
    typography: "{typography.label}"
    rounded: "{rounded.sm}"
    padding: "0 10px"
    height: "27px"
  status-badge-info:
    backgroundColor: "{colors.info-bg}"
    textColor: "{colors.info-fg}"
    typography: "{typography.label}"
    rounded: "{rounded.sm}"
    padding: "0 10px"
    height: "27px"
  status-badge-warning:
    backgroundColor: "{colors.warning-bg}"
    textColor: "{colors.warning-fg}"
    typography: "{typography.label}"
    rounded: "{rounded.sm}"
    padding: "0 10px"
    height: "27px"
  status-badge-review:
    backgroundColor: "{colors.review-bg}"
    textColor: "{colors.review-fg}"
    typography: "{typography.label}"
    rounded: "{rounded.sm}"
    padding: "0 10px"
    height: "27px"
  status-badge-danger:
    backgroundColor: "{colors.danger-bg}"
    textColor: "{colors.danger-fg}"
    typography: "{typography.label}"
    rounded: "{rounded.sm}"
    padding: "0 10px"
    height: "27px"
  notice-info:
    backgroundColor: "{colors.info-bg}"
    textColor: "{colors.info-fg}"
    rounded: "{rounded.md}"
    padding: "12px 14px"
  input:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text}"
    typography: "{typography.body}"
    rounded: "{rounded.sm}"
    padding: "10px 12px"
    height: "44px"
  input-invalid:
    backgroundColor: "{colors.danger-bg}"
  nav-link:
    backgroundColor: "transparent"
    textColor: "{colors.text-muted}"
    rounded: "{rounded.md}"
    padding: "0 13px"
    height: "44px"
  nav-link-active:
    backgroundColor: "{colors.harbour-teal-soft}"
    textColor: "{colors.harbour-teal}"
  panel:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.md}"
  metric-card:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.md}"
    padding: "18px"
---

# Design System: ClaimFile

The source of truth for how ClaimFile looks and behaves. Every value here
exists as a CSS variable in `frontend/src/styles.css`; components use the
variables, never raw hex values or one-off sizes.

## Overview

**Creative North Star: "The Steady Caseworker"**

ClaimFile should feel like a calm, competent person handling your claim. It
tells you where things stand and what happens next before it shows any detail,
it puts the evidence next to every automated finding, and it never alarms.
That same caseworker is equally at home with both audiences. **Claimants** are
individuals after a car accident, often stressed, who visit a few times per
claim, frequently on a phone. **Reviewers** are insurance staff who use it daily
on a desktop and need to clear a queue quickly and defensibly.

The mood is **calm, trustworthy, clear**. ClaimFile keeps its own identity
(Harbour Teal, Manrope + DM Sans). For UX tone it borrows from the GOV.UK
Design System (plain language, accessibility first); for the reviewer queue it
borrows the quiet density of the Linear and Stripe dashboards. The style is
"Accessible & Ethical": WCAG AA contrast, visible focus, 44px touch targets,
reduced motion respected. Light theme only for now; tokens are named so dark
mode can be added later. Density is comfortable on claimant pages and
standard-dense in the reviewer queue and tables.

Components are **quiet and dependable**: soft 10px corners, hairline borders,
almost no shadow, and colour only where it carries meaning.

**Key Characteristics:**
- Say what happens next. Every claim screen answers "where is my claim, and do I need to do anything?" in plain words before showing details.
- One colour, one meaning. Status colours mean the same thing on every screen and for both roles. Harbour Teal is for actions and navigation, never a status.
- Show the evidence. An automated finding is always shown with the document it came from. People make the decision, and the UI says so.
- Readable first. Text meets 4.5:1 contrast; nothing important is lighter grey than `--text-muted`.

## Colors

A cool, near-white canvas with one teal for action and five status tones that each carry exactly one meaning.

### Primary
- **Harbour Teal** (`--teal`, #087f78): primary buttons, links, active nav, focus ring (4.86:1 on white).
- **Harbour Teal Dark** (`--teal-dark`, #066c66): hover on primary; teal text on `--teal-soft`; top of the sign-in brand gradient.
- **Harbour Teal Darker** (`--teal-darker`, #055a55): bottom of the sign-in brand gradient.
- **Harbour Teal Bright** (`--teal-bright`, #1fa58a): graphics only (dots, progress, eyebrow rule), 3:1. Never text.
- **Harbour Teal Soft** (`--teal-soft`, #eaf6f4): selected/active backgrounds.
- **Harbour Teal Line / Ring** (`--teal-line` #cfe7e3, `--teal-ring` #d7eeeb): teal borders; the soft halo around a focused input.
- **On Brand** (`--on-brand` #e8f5f3, `--on-brand-muted` #bfe3de, `--on-brand-accent` #a8e3da): text on the dark teal sign-in panel.

### Neutral
- **Page** (`--bg`, #f6f8fb): page background.
- **Surface** (`--surface`, #ffffff): cards, panels, tables.
- **Surface Subtle / Muted / Sunken** (#f9fbfc / #f4f7f9 / #e2e9ef): inset areas, table headers, tracks.
- **Line Soft / Line / Line Strong** (#eff2f5 / #e7edf2 / #d6dfe6): dividers / borders / emphasised borders.
- **Control Border** (`--control-border`, #7f96ac): input outlines, 3:1 on white.
- **Scrim** (`--scrim`, rgba(23, 43, 66, 0.38)): behind the mobile drawer.
- **Text Strong** (#192e45): headings. **Text** (#20334a): body. **Text Secondary** (#44586d): supporting body text. **Text Muted** (#637283): labels and metadata, at least 4.5:1 on every surface above. **Text Inverse** (#ffffff): text on teal.

`--text-faint` is retired: it measured 2.8:1. Use `--text-muted` instead;
only disabled controls may be lighter.

### Status tones

Each tone has four tokens: `-fg` text (≥4.6:1 on its background), `-bg` soft
background, `-line` border, and `-solid` for dots and fills (≥3:1 on white).
Badges, notices, metric icons and card edges all use the same tone for the
same meaning.

| Tone | fg | bg | Meaning | Claim statuses |
|---|---|---|---|---|
| `success` | #257e5b | #eef9f2 | Done, good outcome, confirmation | `complete`, `approved`; "Account created" |
| `info` | #476eb0 | #f0f5ff | System is working; neutral information | `pending`, `in_progress` |
| `warning` | #a15f2c | #fff5ec | The **claimant** must act | `waiting_for_documents` |
| `review` | #735fba | #f4f1ff | With a **reviewer** | `human_approval`, `needs_internal_review`, `budget_exceeded` |
| `danger` | #b74c4c | #fff1f1 | Negative outcome or error | `terminated`, `rejected`; form and API errors |

The same mapping drives the dashboard metric cards for both roles: "Action
needed" / "Awaiting claimant" are `warning`, "Under review" / "Needs decision"
are `review`.

### Named Rules
**The One Colour, One Meaning Rule.** A status tone means the same thing on every screen and for both roles. Harbour Teal is for actions and navigation and is never used to signal a status.

**The Readable First Rule.** Text meets 4.5:1; focus rings and control borders meet 3:1. Nothing important is lighter than `--text-muted`.

## Typography

**Display / Heading Font:** Manrope (with DM Sans, system-ui)
**Body Font:** DM Sans (with system-ui, -apple-system, Segoe UI)

**Character:** Manrope's heavy, slightly geometric weights give headings a confident, steady voice; DM Sans keeps body text open and friendly at small sizes.

### Hierarchy
- **Display** (Manrope 800, 30px): dashboard metric values.
- **Headline** (Manrope 800, `clamp(26px, 2.4vw, 32px)`, 1.2, -0.8px tracking; 24px on mobile): page titles (h1).
- **Title** (Manrope 800, 17px): panel and form section titles (h2).
- **Body** (DM Sans 400, 16px, 1.5): claimant pages and form inputs. Inputs are always 16px (prevents zoom on iOS).
- **Body dense** (DM Sans 400, 14px, 1.5): reviewer tables, metadata, base body size.
- **Label** (DM Sans 600, 12–13px, 1.4): labels, badges, captions. Eyebrows and the sidebar section label are 700 with 1.35–1.4px tracking.

### Named Rules
**The 12px Floor Rule.** Nothing below 12px.

## Layout

- **Spacing scale** (`--space-*`): 4, 8, 12, 16, 20, 24, 32, 40, 56px. Use the scale only.
- **App shell:** fixed 250px sidebar (`--sidebar-w`) on the left, sticky 68px topbar (translucent white with 12px backdrop blur), content beside it. Below 900px the sidebar collapses to a 72px icon rail; below 600px it becomes a slide-in drawer over `--scrim`.
- **Dashboard:** four metric cards in a grid (15px gap), then the claims panel.
- **Reviewer decision:** evidence on the left, sticky decision panel on the right; stacks below 1100px.
- **Sign-in:** two equal columns, dark teal brand panel and form.
- **Breakpoints (max-width):** 1200px, 1100px, 900px, 600px.
- Works at 375, 768, 1024 and 1440px without horizontal page scroll.

## Elevation & Depth

Nearly flat. Depth comes from the cool `--bg` canvas against white surfaces
and hairline borders; shadows are so faint they read as a lift, not a float.
Only three shadows exist.

### Shadow Vocabulary
- **Card** (`--shadow-card`: `0 2px 7px rgba(26, 48, 72, 0.03)`): panels.
- **Raised** (`--shadow-raised`: `0 1px 3px rgba(25, 46, 69, 0.12)`): a selected tab or control.
- **Overlay** (`--shadow-overlay`: `0 10px 35px rgba(21, 46, 71, 0.1)`): toast, mobile drawer, sign-in card.

### Named Rules
**The Three Shadows Rule.** No other shadows. Allowed raw values: translucent white over the brand panel and sticky topbar (`rgba(255,255,255,…)`) and `--scrim`. Everything else is a token.

## Shapes

Soft, consistent corners and 1px borders.

- `--radius-sm` 6px: badges, chips, small buttons, inputs.
- `--radius` 10px: buttons, cards, panels, notices, nav links.
- `--radius-lg` 14px: large standalone surfaces (sign-in card, brand mark).
- `--radius-pill` 999px: pills (connection status, eyebrow rule).
- `50%` only for circles (status dots, avatars).
- The claim status card adds a 4px left edge in its tone's `-solid` colour; this is the only coloured edge.

## Components

### Buttons
Quiet and dependable: one teal primary per view, everything else outlined.
- **Shape:** `--radius` (10px), 42px tall, 18px side padding, 13.5px / 700.
- **Primary:** Harbour Teal background, white text; hover `--teal-dark`.
- **Secondary:** white with `--line` border, `--text-secondary` text; hover `--bg`.
- **Danger (Reject):** white with `--danger-line` border, `--danger-fg` text; hover `--danger-bg`. Always asks for a reason.
- **Small:** 35px tall, 13px padding, 12.5px.
- **Disabled:** 0.55 opacity, `not-allowed` cursor.
- **Touch:** minimum 44px tall on touch layouts (see Known gaps).

### Status badge
- Tone `-bg` background, `-line` border, `-fg` text, 6px `currentColor` dot, `--radius-sm`, 27px tall, 12px / 600.
- Always a text label as well as colour, never colour alone.

### Notice
- 12px 14px padding, `--radius`, tone border/background/text, leading icon.
- `info` for neutral messages, `success` for confirmations, `warning` when the user must act, `danger` (`.notice-error`) for errors. Errors sit next to the field they concern, not only at the top.

### Toast
- Bottom-right, white surface, `--success-line` border, `--success-fg` text, `--shadow-overlay`.

### Panels and metric cards
- **Panel:** white, 1px `--line` border, `--radius`, `--shadow-card`; heading padding 21px 22px 17px.
- **Metric card:** white, 1px `--line` border, `--radius`, 18px padding; 36px tinted icon tile in the metric's tone, muted 13px label, 30px Manrope value.

### Inputs / Fields
- Visible label above (13px / 600, `--text-secondary`), never placeholder-only; helper text under the field; required marker in `--danger-fg`.
- **Input:** 44px min height, 10px 12px padding, 1px `--control-border`, `--radius-sm`, 16px text.
- **Focus:** border becomes Harbour Teal plus a 3px `--teal-ring` halo.
- **Invalid:** `--danger-solid` border, `--danger-bg` fill, error text below in `--danger-fg`.
- Required documents clearly marked; multi-step forms show a step indicator ("Step 2 of 4").

### Navigation
- **Sidebar link:** 44px tall, `--radius`, `--text-muted` 14px; hover `--surface-muted`; active Harbour Teal text on `--teal-soft`, weight 700.
- **Topbar:** breadcrumb in 13px muted text with the current page in `--text`; connection pill with a `-solid` dot (success = connected, warning = checking, danger = disconnected).

### Claim status card (signature)
The first thing on a claim page: a panel with a 4px left edge in the status tone, a tone icon tile, a kicker, a plain-language headline and sentence, a "what we need from you" list when the claimant must act, and one action. `data-tone` picks the tone.

### Tables
- Every row is clickable *and* has a real link/button for keyboard users.
- The reviewer queue sorts oldest first.

### Focus
- 3px Harbour Teal outline, 2px offset, on every interactive element, including custom controls (search field, chips, table rows).

## Motion

- 150ms for hover/focus, 200–250ms for panels and dialogs, `ease-out` (`--ease-out`: `cubic-bezier(0.2, 0.8, 0.2, 1)`, `--duration-fast` 150ms, `--duration` 220ms). Exits are faster than entrances.
- Motion only to show change (a claim's status updating, a panel opening).
- Everything is disabled under `prefers-reduced-motion`.

## Do's and Don'ts

### Do:
- **Do** use the CSS variables in `frontend/src/styles.css` for every colour, radius, shadow and spacing value.
- **Do** use one primary (Harbour Teal) button per view.
- **Do** pair every status colour with a text label.
- **Do** show an automated finding next to the document it came from.
- **Do** tell the user what happens next, in plain words, before showing details.
- **Do** keep inputs at 16px and touch targets at 44px or more.

### Don't:
- **Don't** use Harbour Teal to mean a status, or a status tone for an action.
- **Don't** use `--text-faint` or any grey lighter than `--text-muted` for meaningful text.
- **Don't** set text below 12px.
- **Don't** add shadows beyond the three in the Shadow Vocabulary.
- **Don't** put raw hex values in components.
- **Don't** rely on placeholder text as a label.

## Accessibility checklist (before calling UI done)

- [ ] Text contrast ≥4.5:1; focus ring and control borders ≥3:1
- [ ] Every interactive element reachable and visible with the keyboard
- [ ] Icons that carry meaning have labels; decorative icons are `aria-hidden`
- [ ] Status never shown by colour alone
- [ ] Works at 375, 768, 1024 and 1440px without horizontal page scroll
- [ ] `prefers-reduced-motion` respected

## Known gaps (code vs. rules, as of 2026-10-27)

The rules above are the target; these places in `styles.css` do not meet them yet.

- `.btn` is 42px tall on every layout; the 44px touch rule is not applied on mobile.
- 14 declarations set text at 9–11px (eyebrows, sidebar section label, some mobile labels), below the 12px floor.
- `--ease-out`, `--duration-fast` and `--duration` are defined but unused; transitions use raw `0.15s`–`0.22s ease`.
