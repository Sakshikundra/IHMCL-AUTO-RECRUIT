# IHMCL Auto Recruit Validator — Backend

A real, persistent backend for the existing React frontend (`services/api.js`), built with
**FastAPI + SQLite**, an **IHMCL-branded login/signup gateway** with 30‑day cookie sessions, and a
**4-stage Gemini-powered screening pipeline**.

The frontend is untouched — this backend implements exactly the routes it already calls
(`http://localhost:3001/api/...`), so you just run both and they talk to each other.

---

## 1. What's inside

```
backend/
  app/
    main.py              FastAPI app: CORS, routers, auth gateway pages, DB init, demo seed
    config.py             Reads .env
    database.py            SQLAlchemy engine/session (SQLite by default)
    models.py               User / Job / Application / MatchResult tables
    auth.py                  JWT + bcrypt password hashing
    deps.py                   Auth dependency — accepts Bearer token OR the 30-day cookie
    gemini_client.py           Thin Gemini wrapper (JSON-mode, retries, fence-stripping)
    schemas.py                  Pydantic request bodies
    routers/
      auth_router.py             /api/auth/signup /login /logout /me
      jobs_router.py              /api/jobs ... + /api/jobs/extract-jd (Stage 1)
      applications_router.py       /api/jobs/:id/applications ... + /evaluate + /override
    pipeline/
      extract_text.py              PDF -> text with [PAGE n] markers (for citations)
      import_utils.py               Excel candidate-sheet parsing + ZIP document matching
      stage1_jd_extraction.py        STAGE 1 — JD PDF -> structured criteria (Gemini)
      stage2_resume_parsing.py        STAGE 2 — resume -> structured candidate profile (Gemini)
      stage3_rule_matching.py          STAGE 3 — checklist rule x resume -> pass/fail + citation (Gemini)
      stage4_verdict.py                 STAGE 4 — deterministic verdict aggregation (no LLM call)
      orchestrator.py                    Runs Stage 2 -> 3 -> 4 for one candidate
    templates/
      login.html / signup.html      IHMCL-branded auth pages (logo, navy theme)
    static/
      css/auth.css, img/ihmcl-logo.png
  storage/                 Uploaded JD PDFs, resumes, ZIPs land here (gitignored)
  requirements.txt
  .env.example
```

## 2. The 4-stage pipeline

| Stage | Trigger | What it does | LLM? |
|---|---|---|---|
| **1. JD Extraction** | `POST /api/jobs/extract-jd` (recruiter uploads the advertisement PDF, e.g. the IHMCL job notice) | Extracts the target post's criteria (experience, skills, education, location, custom rules like age/pay-scale) into the exact shape the Criteria Editor expects | ✅ Gemini |
| **2. Resume Parsing** | Runs automatically inside `/evaluate`, once per candidate | Reads the candidate's matched PDF and pulls out DOB, education, experience (years), skills, ID number | ✅ Gemini |
| **3. Rule Matching** | Runs automatically inside `/evaluate`, right after Stage 2 | Checks the job's **locked** checklist rule-by-rule against the candidate's documents; every `passed` result must carry a quoted citation + page number, otherwise it's `unverified`/`missing_document` | ✅ Gemini |
| **4. Verdict** | Runs automatically inside `/evaluate`, right after Stage 3 | Deterministic policy: any failed **hard** rule → `not_eligible`; any unverified/missing hard rule → `semi_eligible`; all hard rules passed → `eligible`. Kept LLM-free on purpose so the final decision is always explainable from Stage 3's evidence | ❌ rule-based |

`POST /api/applications/{id}/evaluate` runs stages 2→4 in one call — this is what the frontend's
bulk-upload flow triggers for every imported candidate.

## 3. Setup

### Prerequisites
- Python 3.11+
- A Gemini API key ([Google AI Studio](https://aistudio.google.com/apikey))
- Node.js (already needed for the existing frontend)

### Install
```bash
cd backend
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# now edit .env and set GEMINI_API_KEY (required) and JWT_SECRET (recommended)
```

### Run
```bash
uvicorn app.main:app --reload --port 3001
```
The API is now live at `http://localhost:3001`. SQLite database `recruit.db` is created
automatically on first run, along with two **demo accounts** matching the credentials already
hardcoded in `services/api.js` (so the React app keeps working with zero changes):

| Role | Email | Password |
|---|---|---|
| Recruiter | `recruiter@recruitment.local` | `Recruiter@123456` |
| Hiring Manager | `manager@recruitment.local` | `Manager@123456` |

### Run the frontend (unchanged)
```bash
cd frontend
npm install
npm run dev
```
It runs on `http://localhost:5173` and talks to the backend on port 3001 automatically.

## 4. The auth gateway (IHMCL-branded, 30-day cookies)

This sits **in front of** the app, separate from the frontend's own silent Bearer-token
auto-login (which still works unchanged, for the demo accounts above):

- `http://localhost:3001/login` — IHMCL-branded sign-in page
- `http://localhost:3001/signup` — create a new recruiter / hiring-manager account
- On success, both set an **httpOnly cookie** (`access_token`, 30-day expiry) and redirect to the
  React app (`FRONTEND_ORIGIN`, default `http://localhost:5173`)
- `POST /api/auth/logout` clears the cookie
- `GET /api/auth/me` returns the signed-in user (cookie **or** Bearer token accepted)

Every protected API route accepts **either** an `Authorization: Bearer <token>` header (what the
React app sends) **or** the 30-day cookie (what the branded login page sets) — same JWT under the
hood, two ways to present it.

> Because the frontend and the auth gateway currently run on different ports, cookies set on
> `:3001` aren't sent by the frontend's own `fetch` calls automatically — that's expected. The
> gateway's job is the human sign-in ceremony (and it works standalone against
> `/api/auth/*` + Swagger at `/docs`); the SPA keeps using its own Bearer flow, per the demo
> credentials table above. If you want one unified session, deploy both behind the same origin
> (e.g. an nginx reverse proxy) and point the frontend at relative `/api` URLs — happy to wire
> that up if useful.

## 5. Testing Stage 1 with the sample JD

The uploaded `IHMCL-Job-Advertisement-April-2026.pdf` (Lead Systems Engineer, Lead IT &
Cybersecurity Architect, etc.) is a good real-world test file for `/api/jobs/extract-jd` — it has
multiple posts in one PDF, which Stage 1's prompt is specifically built to disambiguate using the
`jobId`/title hint.

The `IHM_JA_1900_10001_downloaded_files.zip` bundle (a resume, marksheets, experience letter,
payslips, signature, photo for one applicant) is a good sample for testing the bulk-import +
Stage 2/3/4 flow — it mirrors IHMCL's real applicant-document naming convention
(`<id>_<Name>-<DocType>.<ext>`), which `import_utils.match_resume_for_candidate` is built to match.

## 6. API summary

```
POST   /api/auth/signup                          {email,password,firstName,lastName,role}
POST   /api/auth/login                            {email,password}
POST   /api/auth/logout
GET    /api/auth/me

GET    /api/jobs
GET    /api/jobs/:id
POST   /api/jobs                                  {title,postingCode,description}
POST   /api/jobs/:id/lock-checklist                {rules:[...]}
POST   /api/jobs/extract-jd                         multipart: file (PDF), jobId

GET    /api/jobs/:jobId/applications?limit&verdict
POST   /api/jobs/:jobId/applications/import         multipart: file (xlsx)
POST   /api/jobs/:jobId/applications/import-zip      multipart: file (zip)
POST   /api/applications/:id/evaluate                runs Stage 2 -> 3 -> 4
POST   /api/applications/:id/override                {verdict, reason}
```

Interactive Swagger docs: `http://localhost:3001/docs`

## 7. Notes on "long-term workable"

- **Persistence**: SQLite file (`recruit.db`) — survives restarts, no external DB needed. Swap
  `DATABASE_URL` in `.env` for Postgres/MySQL later with zero code changes (SQLAlchemy).
- **Gemini calls are isolated** to `gemini_client.py` and the 3 stage files that use it — swapping
  models, adding caching, or adding a queue for large bulk batches later is a small, contained change.
  `GEMINI_MODEL` is a one-line env var, not hardcoded.
  - JSON parsing is defensive (strips markdown fences, retries once asking the model to fix its own
    output) so occasional model formatting hiccups don't crash a batch run.
- **Files are stored on disk** under `storage/`, referenced by path in SQLite — for real production
  scale, swap this for S3/Blob storage behind the same `resume_path` field.
- **Passwords** are bcrypt-hashed; **sessions** are JWT (`JWT_SECRET` in `.env` — change it before
  any real deployment).
