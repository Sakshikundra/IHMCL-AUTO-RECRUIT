# IHMCL Auto Recruit Validator — Full Package

This is your React frontend (**unchanged**) + a new, workable **FastAPI + SQLite backend**
with an **IHMCL-branded login/signup gateway** (30-day cookie sessions) and a
**4-stage Gemini-powered screening pipeline**.

```
ihmcl-auto-recruit/
  backend/     <- new. FastAPI, SQLite, Gemini pipeline, auth gateway. See backend/README.md
  frontend/    <- your original React app, untouched (node_modules/dist excluded — run npm install)
  samples/     <- test files to try the pipeline with immediately
    IHMCL-Job-Advertisement-April-2026.pdf   -> use with "Extract from JD" (Stage 1)
    sample_candidate_documents.zip            -> use as the bulk-screening document ZIP (Stage 2/3)
    sample_candidate_sheet.xlsx               -> matching candidate sheet for bulk-screening
```

## Quick start (5 minutes)

**1. Backend**
```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edit .env -> set GEMINI_API_KEY (get one free at https://aistudio.google.com/apikey)
uvicorn app.main:app --reload --port 3001
```

**2. Frontend** (separate terminal, unchanged)
```bash
cd frontend
npm install
npm run dev
```
Open the URL Vite prints (usually `http://localhost:5173`) — the app auto-logs in as the demo
Recruiter account and talks to your new backend on port 3001. No frontend code changes needed.

**3. Try the branded login gate** (separate from the app's own auto-login)

Visit `http://localhost:3001/login` — sign in with:
- `recruiter@recruitment.local` / `Recruiter@123456`, or
- `manager@recruitment.local` / `Manager@123456`

or hit **Create an account** to sign up your own user. Either way you get a 30-day cookie and
land back on the React app.

**4. Try the pipeline end to end**
1. In the app, go to **Job Description**, create a new profile, and use **Extract from JD** with
   `samples/IHMCL-Job-Advertisement-April-2026.pdf` (Stage 1 — Gemini reads the PDF and pre-fills
   the criteria editor). Save/lock the checklist.
2. Go to **Shortlist Candidates** (bulk screening) and upload `sample_candidate_sheet.xlsx` +
   `sample_candidate_documents.zip`. Watch it import, then automatically run Stages 2→4
   (resume parsing → rule verification with citations → verdict) for the candidate.
3. Check **Manual Review** / **Approve for Interview** — verdicts and evidence trails should be
   populated from real Gemini output, not mock data.

Full API reference, architecture notes, and "why it's built this way" are in
`backend/README.md`.
