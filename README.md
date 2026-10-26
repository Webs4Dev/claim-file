# ClaimFile

Motor insurance claim processing. Claimants submit a claim with supporting
documents; a LangGraph pipeline of agents validates the documents, extracts
the facts, investigates them against the policy wording (RAG over the policy
PDFs) and reviews the result. A human reviewer makes the final decision.

- **Backend:** FastAPI, LangGraph, OpenAI, Chroma + BM25 retrieval, Redis
- **Frontend:** React + Vite (`frontend/`)

## Run locally

Requirements: Python, Node and Docker (tested with Python 3.14 and Node 26).

```bash
# 1. Redis
docker compose up -d

# 2. Backend
python -m venv venv
venv/bin/pip install -r requirements.txt
cp .env.example .env                    # then fill in OPENAI_API_KEY
venv/bin/python -m scripts.build_index  # once: index the policy PDFs
venv/bin/uvicorn app.main:app --port 8000

# 3. Frontend (separate terminal)
cd frontend
npm install
npm run dev                             # http://localhost:5173
```

The frontend calls the API through Vite's `/api` proxy, so the session cookie
is same-origin. Open the app on `http://localhost:5173`.

## Accounts

- **Claimants** create their own account on the sign-in page. They see only
  their own claims.
- **Reviewers** see every claim and approve or reject the ones awaiting human
  review. They cannot sign up through the app; create one with:

  ```bash
  venv/bin/python -m scripts.create_reviewer
  ```

## Environment variables

Backend (`.env`, see `.env.example`):

| Name | Purpose |
|---|---|
| `OPENAI_API_KEY` | OpenAI key used by all agents (required) |
| `OPENAI_MODEL` | Model name |
| `MAX_STEPS`, `MAX_TOKENS`, `MAX_COST` | Per-claim processing budget |
| `COOKIE_SECURE` | `true` when served over HTTPS |
| `ALLOWED_ORIGINS` | Comma-separated browser origins allowed to call the API |

Frontend (`frontend/.env`, see `frontend/.env.example`):

| Name | Purpose |
|---|---|
| `VITE_API_BASE_URL` | API base path; keep `/api` in development |

## Tests

```bash
# Fast, no LLM calls (needs Redis)
venv/bin/python -m pytest tests/test_auth_api.py tests/test_human_gate.py tests/test_investigator_status.py -q

# Policy retrieval checks
venv/bin/python -m tests.eval_policy_retrieval

# 8 end-to-end scenario claims against the running API (uses the LLM)
venv/bin/python -m scripts.make_test_claims
venv/bin/python -m tests.run_test_claims
```

`venv/bin/python -m utils.clear_redis` deletes all claims (asks first).
