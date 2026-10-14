# ClaimFile Frontend

Responsive React + Vite frontend for the ClaimFile motor insurance portal.

## Run

Requires Node.js 18+.

```bash
npm install
npm run dev
```

Open the local URL printed by Vite. `npm run build` creates `dist/`.

## Backend

Defaults to `http://127.0.0.1:8000`. Copy `.env.example` to `.env` and set
`VITE_API_BASE_URL` to change it. All endpoint paths live in `src/api.js`.

| Action                       | Request                              |
| ---------------------------- | ------------------------------------ |
| Health check (every 30s)     | `GET /health`                        |
| List claims                  | `GET /claims`                        |
| Submit claim                 | `POST /claims` (multipart)           |
| Claim details                | `GET /claims/{claim_id}`             |
| Upload follow-up documents   | `POST /claims/{claim_id}/documents`  |

`POST /claims` sends `claim_form` (JSON string) plus one file field per document.

If `GET /claims` does not exist, the dashboard lists claims submitted from this
browser (fetched individually by ID). With none, it shows labelled demo rows.

## Features

- Hash routing (`#/`, `#/claims`, `#/new`, `#/claims/ID`, `#/help`): back button, refresh and deep links work
- Auto-refresh of claims and claim details while a claim is pending / in progress
- Live API connection indicator (click to re-check)
- Multi-step claim form with highlighted missing fields and a 10 MB file-size check
- Search, status filters (with counts) and newest-first sorting
- Responsive layout with a slide-over menu on phones

## Structure

```
src/
  api.js  utils.js  styles.css  App.jsx  main.jsx
  hooks/       useHashRoute, useClaims, useClaim, useApiHealth
  components/  Header, Sidebar, StatusBadge, DocumentUpload, Metric, Notice, Toast
  pages/       Dashboard, NewClaim, ClaimDetails, Help
```
