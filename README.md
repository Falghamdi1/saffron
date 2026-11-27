# Saffron AI

A restaurant ordering assistant that remembers how each diner eats. It learns allergies,
diets, tastes and budget from ordinary conversation, recommends only real menu items, and
shows the diner everything it remembers and how that changed.

**Deep-dive challenge:** reliable long-term memory and personalization.

| | |
| --- | --- |
| Live application | _Not deployed yet. See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)._ |
| Video walkthrough | _To be recorded._ |

## The core idea

A wrong memory is worse than no memory: a forgotten allergy is dangerous, and an invented
one quietly shrinks the menu forever. So the language model is only allowed to *read*.

1. The model (or a rule-based fallback) turns a message into **candidate** changes.
2. A deterministic **memory policy** decides what each candidate does.
3. A deterministic **recommender** filters hard constraints, then ranks.
4. Reply text and dish cards are built from **menu records**, not generated.

Rules the policy enforces:

- Chat cannot remove an allergy. It flags the request and the diner confirms it.
- Hedged statements ("I think I might be…") stay pending. A pending allergy is still
  avoided; a pending diet is not enforced.
- "Today I want…" shapes the conversation and is never saved.
- Corrections supersede the old record. History is append-only at the database level.

## Run it locally

Needs Python 3.11 and Node 20.19 or newer. No accounts or keys are required: local mode
creates a private PostgreSQL in `.localdb/` and signs diners in by name only.

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements-dev.txt
cd ..\frontend
npm install
npm run build
cd ..\backend
.\.venv\Scripts\python -m uvicorn app.main:create_app --factory --port 8000
```

Open <http://localhost:8000>. On macOS or Linux use `.venv/bin/python`.

To use Gemini for message understanding, copy `.env.example` to `.env` and set
`GEMINI_API_KEY`. For frontend development, run `npm run dev` in `frontend/` alongside the
backend; `/api` is proxied.

## Try it

| Say | What to look for |
| --- | --- |
| "I'm allergic to nuts. Which desserts can I have?" | Two allergies saved; only safe desserts |
| New conversation: "What should I have for dinner?" | The allergy still applies |
| "I'm not allergic to nuts anymore" | Kept until you press confirm |
| "I usually like mild food", then "today I want something spicy" | Saved preference unchanged |
| "I think I might be vegetarian" | Asked, not assumed |
| "Compare butter chicken and chicken vindaloo" | Side-by-side table with conflicts marked |
| "Do you have sushi?" | Says it is not on the menu |

**My preferences** shows every record, its source sentence and its history.

## Tests and evaluation

```powershell
cd backend
.\.venv\Scripts\python -m pytest
.\.venv\Scripts\python -m evaluation.run
```

Add `--llm` to also score Gemini (needs a key). Latest measured results are in
[docs/EVALUATION.md](docs/EVALUATION.md). No hard-constraint violation was found in the
constraint sweep. On 30 unseen phrasings Gemini matched 26 exactly and the rule-based
fallback 13, so the fallback is a safety net, not a substitute for the model.

## Layout

```text
backend/app/
  understanding/    rules, Gemini adapter, reconciliation of the two
  memory/           policy (pure), repository (SQL), service (only write path)
  recommendation/   filtering and ranking (pure), dish name matching
  chat/             one turn: understand, remember, recommend, reply
  api.py auth.py db.py
backend/data/menu.json     24 dishes, 4 categories
backend/evaluation/        scenarios, held-out phrasings, report generator
frontend/src/              React client
supabase/migrations/       schema and Row Level Security
```

## Documentation

- [Requirements checklist](docs/REQUIREMENTS.md)
- [Architecture](docs/ARCHITECTURE.md) and [database schema](docs/DATABASE.md)
- [Design decisions](docs/DECISIONS.md)
- [Evaluation report](docs/EVALUATION.md)
- [Known limitations](docs/LIMITATIONS.md)
- [Deployment](docs/DEPLOYMENT.md)
- [Video walkthrough outline](docs/VIDEO_WALKTHROUGH.md)

## Use of AI tools

AI coding assistants were used extensively for implementation, research and drafting.
Behaviour described here is backed by the tests and the generated evaluation report;
anything not verified is listed under known limitations.

The restaurant, menu and allergen data are fictional sample data.
