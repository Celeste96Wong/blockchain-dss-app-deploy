# Blockchain Adoption Readiness Assessment — Deployable Version (Flask + Vercel)

This is the **deployment-ready** version of the MVP prototype, rebuilt from the original
Streamlit version per supervisor feedback. It uses **Flask** (not Streamlit, since Streamlit
does not deploy cleanly on Vercel) and **Vercel KV** for persistent data storage, so that
Expert Validators and SME participants can be sent a public link and their responses are
actually saved (the original Streamlit demo intentionally did not store any data).

---

## What changed from the original `blockchain-dss-app` version

| Change | Reason |
|---|---|
| Streamlit → Flask | Streamlit does not deploy natively on Vercel; Flask does |
| No storage → Vercel KV | Supervisor requires real data collection from Expert/SME participants |
| Consent: added Name + Email + Affiliation | Supervisor clarified personal data *is* collected (for contact purposes) — only quotes/reporting stay anonymous |
| "Stage 0" renamed to "Profile" | The official Proposal document only defines Stage 1/2/3 — "Stage 0" was an internal dev-only name and should not appear in the live system |
| AHP pairwise questions: free-text → choice-based | Free-text answers ("Economic more important, scale 5") were inconsistent to parse; now uses two dropdown/radio choices instead, with the Saaty (1980) scale explained on-screen |
| Radar chart: Plotly → Chart.js | Chart.js works without a Python plotting backend, better suited to a Flask/HTML deployment |

**Fuzzy AHP-TOPSIS logic itself (`fuzzy_engine.py`) is unchanged** — it was already validated
and is reused as-is.

---

## Project structure

```
blockchain-dss-app-deploy/
├── api/
│   └── index.py          ← Main Flask app (Vercel entrypoint)
├── templates/             ← HTML pages (Jinja2)
├── static/
│   └── style.css
├── fuzzy_engine.py         ← Stage 2 core logic (unchanged from original)
├── llm_explainer.py        ← Stage 3 LLM logic (unchanged from original)
├── questions.py            ← All question banks (consent, profile, Stage 1/2, validation surveys)
├── db.py                   ← Vercel KV storage wrapper
├── vercel.json              ← Vercel deployment config
├── requirements.txt
├── .env
└── .gitignore
```

---

## Local setup (test before deploying)

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Add your OpenAI API key

```bash
cp .env.example .env
```

Then edit `.env` and paste your real key:

```
OPENAI_API_KEY=sk-your-real-key-here
FLASK_SECRET_KEY=<run the command in .env.example to generate one>
```

Leave `KV_REST_API_URL` and `KV_REST_API_TOKEN` blank for local testing — the app will use
temporary in-memory storage instead (see "Local vs Production storage" below).

### 3. Run locally

```bash
python api/index.py
```

Open `http://localhost:5000` in your browser.

---

## Deploying to Vercel (so you can send a link to Supervisor / Experts / SMEs)

### Step 1 — Push this folder to a GitHub repository

```bash
cd blockchain-dss-app-deploy
git init
git add .
git commit -m "Initial deployable version"
git branch -M main
git remote add origin <your-github-repo-url>
git push -u origin main
```

### Step 2 — Import the repo into Vercel

1. Go to [vercel.com](https://vercel.com) and log in (GitHub login works directly).
2. Click **"Add New Project"** and select this GitHub repository.
3. Vercel will auto-detect the Python runtime from `vercel.json` — you don't need to change
   any build settings.

### Step 3 — Add environment variables in Vercel

In your Vercel project → **Settings → Environment Variables**, add:

```
OPENAI_API_KEY = sk-your-real-key-here
FLASK_SECRET_KEY = <a random string>
```

### Step 4 — Connect a Vercel KV database

1. In your Vercel project → **Storage** tab → **Create Database** → choose **KV**.
2. Follow the prompts to connect it to this project.
3. Vercel automatically injects `KV_REST_API_URL` and `KV_REST_API_TOKEN` into your
   deployment — **you do not need to set these manually**.

### Step 5 — Deploy

Click **Deploy**. Once finished, Vercel gives you a public URL
(e.g. `https://your-project-name.vercel.app`) — this is the link you send to your
Supervisor for review, and later to Expert Validators and SME participants.

---

## Local vs Production storage (important to understand)

```
Local development (no KV env vars set):
  → data is stored in an in-memory Python dictionary
  → this data disappears every time you stop the app
  → fine for testing the flow, NOT for real data collection

Production (deployed on Vercel with KV connected):
  → data is stored persistently in Vercel KV
  → survives across sessions, deployments, and restarts
  → this is what you need before sending links to real participants
```

**Do not start collecting real Expert/SME responses until you have confirmed the Vercel KV
database is connected and working in production** — check this by completing one test
assessment on your live Vercel URL, then verifying in the Vercel KV dashboard (Storage tab)
that a `session:...` key was created.

---

## Where API calls happen (cost awareness)

Only one function calls the OpenAI API: `generate_llm_explanation()` in `llm_explainer.py`,
triggered once per completed Stage 2 submission. Everything else (Fuzzy AHP-TOPSIS
calculations, diagnostic rules, the radar chart) runs locally/client-side and does not use
any API quota.

---

## What personal information is collected, and why

Per standard research ethics practice (e.g. Tilburg University and ICPSR informed consent
guidelines), this system collects the **minimum necessary identifying information**:

- **Full Name** (required)
- **Email** (required) — used to contact participants regarding this research
- **Organisation/Affiliation** (optional) — used to help distinguish Academic vs Industry experts

This identifying information is stored together with the response record in Vercel KV, but
**any quotes, findings, or reports shared publicly will always be anonymised** — names and
companies will never be disclosed, consistent with the consent given by each participant
(see the `C2_quote_feedback` consent question).

---

## Known limitations (carried over from the original prototype)

- Dimension weights are still provisional research-constructed seed values (see
  `fuzzy_engine.py` docstring) — pending real Expert AHP pairwise data collected through
  this deployed system.
- Tier cut-points (0.25 / 0.50 / 0.75) are equal-width quartiles, not yet empirically
  calibrated.
- Stage 1 remains strictly binary (Yes/No), following Capocasale & Perboli (2022) faithfully.

---

## Quick test without deploying

```bash
python3 -c "from fuzzy_engine import get_default_weights; print(get_default_weights())"
```

This should print the four dimension weights summing to 1.0, with no errors.

cd blockchain-dss-app-deploy

=============================

# create venv environment
python -m venv venv

# active venv
venv\Scripts\activate

# follow steps
python -m pip install -r requirements.txt
python api/index.py