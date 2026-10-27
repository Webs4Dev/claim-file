<!-- kit: fullstack | version: 6bba92b23617 -->
# Full-stack project rules (kit: fullstack)

## Stack defaults
- Backend: Python + FastAPI, PostgreSQL, Redis when caching/queues are needed, Docker for services.
- Frontend: decide per project; explain the choice. Don't add a framework or library
  just because it is popular: say what problem it solves, whether I could build the
  concept myself first, and whether to adopt it now or later.
- Ask before adding any new dependency.

## Design workflow (every new UI or redesign) - no generic UI
1. Brief first. Before any UI code, agree a short brief with me: who it's for,
   the mood (3 adjectives), 1-2 reference sites or brands, light/dark, density.
2. Design system. Either:
   - pick 1-2 references from Awesome Design MD (list:
     https://github.com/VoltAgent/awesome-design-md/tree/main/design-md, file:
     https://raw.githubusercontent.com/VoltAgent/awesome-design-md/main/design-md/<name>/DESIGN.md),
   - or generate one with the ui-ux-pro-max skill for the product type.
   Then write the project's OWN DESIGN.md (colors, type, spacing, radius, motion,
   component rules). Adapt references; never copy a brand's identity, logo, or
   exact palette for something I'll publish.
3. Build with frontend-design, following DESIGN.md. Use design tokens (CSS
   variables / Tailwind theme), not one-off values. Avoid default fonts
   (Inter, Roboto, Arial) unless DESIGN.md chooses them on purpose.
4. Critique and polish. If the optional Impeccable plugin is installed, run
   `/impeccable critique`, then `/impeccable polish` (also: typeset, colorize,
   layout, bolder, quieter, animate, harden, audit). Without it, critique the
   screenshots from step 5 against DESIGN.md yourself (hierarchy, spacing,
   contrast, type, states) and list the fixes. Fix what is flagged before
   calling the UI done.
5. Look at it. Use Playwright CLI (`playwright-cli --help` for commands) to
   open the page, take screenshots at desktop and mobile widths, and click
   through the main flows. Show me the screenshots. Use Chrome DevTools for
   console errors, failed network requests, and performance.
Skip steps 1-2 for tiny UI tweaks that follow an existing DESIGN.md.

## Project structure
- Keep a README.md with: what it does, how to run it locally, env variables (names only).
- Keep .env.example in sync with every env variable the code reads.
- Docker: provide docker-compose.yml for local services (db, redis) once there is more than one.

## Working style
- Plan first for anything bigger than a small fix: list files to touch and how to verify.
- Write or update tests with each feature (pytest for Python). Run them before saying done.
- Use the code-reviewer agent before commits; security-auditor for auth, payments,
  uploads, webhooks, and before deploys.

## Git (gh CLI)
- Small commits with clear messages (feat:, fix:, refactor:, docs:, test:).
- Never commit to main directly once a project is on GitHub; use a branch + PR via gh.
