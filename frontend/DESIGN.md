# ClaimFile design system

The source of truth for how ClaimFile looks and behaves. Every value here
exists as a CSS variable in `src/styles.css`; components use the variables,
never raw hex values or one-off sizes.

## Brief

| | |
|---|---|
| **Who** | **Claimants**: individuals after a car accident, often stressed, visit a few times per claim, frequently on a phone. **Reviewers**: insurance staff, daily use on a desktop, need to clear a queue quickly and defensibly. |
| **Mood** | Calm, trustworthy, clear |
| **References** | Keep ClaimFile's own identity (teal, Manrope + DM Sans). For UX tone: GOV.UK Design System (plain language, accessibility first). For the reviewer table: Linear / Stripe dashboard (dense, scannable, quiet). |
| **Theme** | Light only for now; tokens are named so dark mode can be added later. |
| **Density** | Comfortable for claimant pages; standard-dense for the reviewer queue and tables. |
| **Style** | "Accessible & Ethical" (UI UX Pro Max recommendation for insurance): WCAG AA contrast, visible focus, 44px touch targets, reduced motion respected. |

## Principles

1. **Say what happens next.** Every claim screen answers "where is my claim, and do I need to do anything?" in plain words before showing details.
2. **One colour, one meaning.** Status colours mean the same thing on every screen and for both roles (see Status colours). Brand teal is for actions and navigation, never a status.
3. **Show the evidence.** An automated finding is always shown with the document it came from. People make the decision, and the UI says so.
4. **Readable first.** Text meets 4.5:1 contrast; nothing important is lighter grey than `--text-muted`.

## Colour

### Brand and neutrals

| Token | Value | Use |
|---|---|---|
| `--teal` | `#087f78` | Primary buttons, links, active nav, focus ring (4.86:1 on white) |
| `--teal-dark` | `#066c66` | Hover on primary; teal text on `--teal-soft` |
| `--teal-soft` | `#eaf6f4` | Selected/active backgrounds |
| `--bg` | `#f6f8fb` | Page background |
| `--surface` | `#ffffff` | Cards, panels, tables |
| `--surface-subtle` / `--surface-muted` / `--surface-sunken` | `#f9fbfc` / `#f4f7f9` / `#e2e9ef` | Inset areas, table headers, tracks |
| `--line-soft` / `--line` / `--line-strong` | `#eff2f5` / `#e7edf2` / `#d6dfe6` | Dividers / borders / emphasised borders |
| `--text-strong` | `#192e45` | Headings |
| `--text` | `#20334a` | Body text |
| `--text-secondary` | `#44586d` | Supporting body text |
| `--text-muted` | `#637283` | Labels, metadata (≥4.5:1 on every surface above) |
| `--text-inverse` | `#ffffff` | Text on teal |
| `--on-brand*` | `#e8f5f3` / `#bfe3de` / `#a8e3da` | Text on the dark teal sign-in panel |

`--text-faint` is retired: it measured 2.8:1. Use `--text-muted` instead;
only disabled controls may be lighter.

### Status colours

Each tone has a text colour (≥4.6:1 on its background), a soft background and
a border. Badges, notices, metric icons and card edges all use the same tone
for the same meaning.

| Tone | Text | Background | Meaning | Claim statuses |
|---|---|---|---|---|
| `success` | `#257e5b` | `#eef9f2` | Done, good outcome, confirmation | `complete`, `approved`; "Account created" |
| `info` | `#476eb0` | `#f0f5ff` | System is working; neutral information | `pending`, `in_progress` |
| `warning` | `#a15f2c` | `#fff5ec` | The **claimant** must act | `waiting_for_documents` |
| `review` | `#735fba` | `#f4f1ff` | With a **reviewer** | `human_approval`, `needs_internal_review`, `budget_exceeded` |
| `danger` | `#b74c4c` | `#fff1f1` | Negative outcome or error | `terminated`, `rejected`; form and API errors |

The same mapping drives the dashboard metric cards for both roles: "Action
needed" / "Awaiting claimant" are `warning`, "Under review" / "Needs decision"
are `review`.

## Typography

| Role | Font | Size / line-height | Weight |
|---|---|---|---|
| Page title (h1) | Manrope | 28px / 1.2 (24px on mobile) | 800 |
| Section title (h2) | Manrope | 18px / 1.3 | 700 |
| Body (claimant pages, forms) | DM Sans | 16px / 1.5 | 400 |
| Body (reviewer tables, metadata) | DM Sans | 14px / 1.5 | 400 |
| Label / badge / caption | DM Sans | 12–13px / 1.4 | 600 |

Nothing below 12px. Inputs are 16px (prevents zoom on iOS).

## Spacing, radius, elevation

- **Spacing scale** (`--space-*`): 4, 8, 12, 16, 20, 24, 32, 40, 56px. Use
  the scale only.
- **Radius**: `--radius-sm` 6px (badges, chips, small buttons), `--radius`
  10px (inputs, buttons, cards), `--radius-lg` 14px (large standalone
  surfaces: sign-in card, brand mark), `--radius-pill` 999px; `50%` only for
  circles.
- **Elevation**: `--shadow-card` (panels), `--shadow-raised` (a selected tab
  or control), `--shadow-overlay` (toast, mobile drawer, sign-in card). No
  other shadows.
- **Allowed raw values**: translucent white over the brand panel / sticky
  topbar (`rgba(255,255,255,…)`) and `--scrim`. Everything else is a token.

## Motion

- 150ms for hover/focus, 200–250ms for panels and dialogs, `ease-out`.
  Exits are faster than entrances.
- Motion only to show change (a claim's status updating, a panel opening).
- Everything is disabled under `prefers-reduced-motion`.

## Components

- **Buttons**: one primary (teal) per view. Secondary is outlined; destructive
  (Reject) uses `danger` and always asks for a reason. Minimum 44px tall on
  touch layouts.
- **Status badge**: tone colour plus a text label, never colour alone.
- **Notice**: `info` (blue) for neutral messages, `success` for confirmations,
  `warning` when the user must act, `danger` for errors. Errors sit next to the
  field they concern, not only at the top.
- **Focus**: 3px `--teal` outline, 2px offset, on every interactive element,
  including custom controls (search field, chips, table rows).
- **Forms**: visible labels (never placeholder-only), helper text under the
  field, required documents clearly marked, step indicator ("Step 2 of 4").
- **Tables**: row is clickable *and* has a real link/button for keyboard users;
  the reviewer queue sorts oldest first.

## Accessibility checklist (before calling UI done)

- [ ] Text contrast ≥4.5:1; focus ring and control borders ≥3:1
- [ ] Every interactive element reachable and visible with the keyboard
- [ ] Icons that carry meaning have labels; decorative icons are `aria-hidden`
- [ ] Status never shown by colour alone
- [ ] Works at 375, 768, 1024 and 1440px without horizontal page scroll
- [ ] `prefers-reduced-motion` respected
