# Full-stack project rules (kit: fullstack)

## Stack defaults
- Backend: Python + FastAPI, PostgreSQL, Redis when caching/queues are needed, Docker for services.
- Frontend: decide per project; explain the choice. Don't add a framework or library
  just because it is popular: say what problem it solves, whether I could build the
  concept myself first, and whether to adopt it now or later.
- Ask before adding any new dependency.

## Project structure
- Keep a README.md with: what it does, how to run it locally, env variables (names only).
- Keep .env.example in sync with every env variable the code reads.
- Docker: provide docker-compose.yml for local services (db, redis) once there is more than one.

## Working style
- Plan first for anything bigger than a small fix: list files to touch and how to verify.
- Write or update tests with each feature (pytest for Python). Run them before saying done.
- After UI changes, verify in the browser with Chrome DevTools: check the console for
  errors and failed network requests, and take a screenshot.
- Use the code-reviewer agent before commits; security-auditor for auth, payments,
  uploads, webhooks, and before deploys.

## Git (gh CLI)
- Small commits with clear messages (feat:, fix:, refactor:, docs:, test:).
- Never commit to main directly once a project is on GitHub; use a branch + PR via gh.
