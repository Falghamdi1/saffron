# Saffron AI

A restaurant ordering assistant that remembers how each diner eats. It learns allergies,
diets, tastes and budget from ordinary conversation, recommends only real menu items, and
shows the diner everything it remembers and how that changed.

**Deep-dive challenge:** reliable long-term memory and personalization.

| | |
| --- | --- |
| Live application | <https://saffron-ai-zrnt.onrender.com> |
| Video walkthrough | _To be recorded._ |

To try the live application, create an account with an email and a password of at least 8
characters; no confirmation email is sent. A second account in a private window shows that
diners are isolated. It runs on free tiers, so the first load may take about a minute.

## The core idea

A wrong memory is worse than no memory: a forgotten allergy is dangerous, and an invented
one quietly shrinks the menu forever. So the language model is only allowed to *read*.

1. The model (or a rule-based fallback) turns a message into **candidate** changes.
2. A deterministic **memory policy** decides what each candidate does.
3. A deterministic **recommender** filters hard constraints, then ranks.
4. Reply text and dish entries are built from **menu records**, not generated.

Rules the policy enforces:

- Chat cannot remove an allergy. It flags the request and the diner confirms it.
- Hedged statements ("I think I might be…") stay pending. A pending allergy is still
  avoided; a pending diet is not enforced.
- "Today I want…" shapes the conversation and is never saved.
- Statements about other people are not saved. Their allergies apply to that conversation.
- Corrections supersede the old record. History is append-only at the database level.

## Languages

English is the default. Arabic, including common Gulf wording, is also supported: a switch
turns the interface right-to-left, replies follow the language of each message, and dishes
have Arabic names, descriptions and ingredients. Memory is stored once in language-neutral
keys, so a preference given in Arabic applies in English and the reverse.

Arabic is **partially verified**: it is covered by automated tests and was checked on screen,
but has not been tested with Gemini or reviewed by a second Arabic reader.

## Architecture

One FastAPI service serves the API and the React client. Supabase provides authentication
and PostgreSQL with Row Level Security; Gemini reads messages and can be swapped out.

```text
message → understanding → memory policy → PostgreSQL → recommender → templated reply
          (Gemini + rules)  (pure code)                (filter, then rank)
```

More in [architecture](docs/architecture.md) and [database schema](docs/database.md).

## Key decisions

| Decision | Why | Cost |
| --- | --- | --- |
| The model proposes, code decides | safety rules are testable and independent of the model | nuance outside the schema is lost |
| Replies are templates | no invented dishes, prices or allergen claims | plain voice |
| Structured memory, no vector store | preferences need exact supersede and retract | free-form facts are not kept |
| Conservative allergen filtering | "may contain" and missing data exclude | some safe dishes are hidden |
| Rules back up the model | the app keeps working without it | the fallback understands far less |

Full reasoning in [design decisions](docs/design-decisions.md).

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
`GEMINI_API_KEY`. For Supabase and hosting, see [deployment](docs/deployment.md). For
frontend development, run `npm run dev` in `frontend/` alongside the backend; `/api` is
proxied.

## Try it

| Say | What to look for |
| --- | --- |
| "I'm allergic to nuts. Which desserts can I have?" | Two allergies saved; only safe desserts |
| New conversation: "What should I have for dinner?" | The allergy still applies |
| "I'm not allergic to nuts anymore" | Kept until you press confirm |
| "I usually like mild food", then "today I want something spicy" | Saved preference unchanged |
| "I think I might be vegetarian" | Asked, not assumed |
| "My wife is allergic to sesame. What mains can she have?" | Sesame avoided in this chat; not saved as yours |
| "Compare butter chicken and chicken vindaloo" | Side-by-side table with conflicts marked |
| "Do you have sushi?" | Says it is not on the menu |
| "عندي حساسية من السمسم. وش تنصحني؟" | Arabic reply; no sesame dishes; the same record shows in English |

**My preferences** shows every record, its source sentence and its history.

## Tests and evaluation

```powershell
cd backend
.\.venv\Scripts\python -m pytest
.\.venv\Scripts\python -m evaluation.run --llm
```

`--llm` needs a Gemini key and takes about twelve minutes. Running without it is quicker but
replaces the report with a rules-only one. Latest measured results are in
[docs/evaluation.md](docs/evaluation.md). No hard-constraint violation was found in the
constraint sweep. On 30 held-out phrasings Gemini matched 28 exactly (measured before its instruction was
extended for Arabic) and the rule-based
fallback 13, so the fallback is a safety net, not a substitute for the model. The latest run
of the scenarios with Gemini was cut short by the free daily quota; the report says what is
and is not complete.

## Known limitations

- Replies are templated and the model sees one message at a time.
- Arabic understanding without Gemini is narrow.
- Without Gemini, many natural phrasings are missed. The free quota is shared, so it can run
  out.
- Whom a sentence is about is decided by wording patterns.
- Allergen data is fictional and cannot rule out cross-contact.
- No frontend tests, load testing or Content-Security-Policy.

The full list is in [limitations](docs/limitations.md).

## Layout

```text
backend/app/
  understanding/    rules, Gemini adapter, reconciliation of the two
  memory/           policy (pure), repository (SQL), service (only write path)
  recommendation/   filtering and ranking (pure), dish name matching
  chat/             one turn: understand, remember, recommend, reply
  api.py auth.py db.py
backend/data/menu.json     24 dishes, 4 categories
backend/evaluation/        scenarios, sentence sets, report generator, live check
frontend/src/              React client
supabase/migrations/       schema and Row Level Security
```

## Documentation

- [Submission checklist](docs/final_submission_checklist.md): every requirement, with status
- [Architecture](docs/architecture.md), [database schema](docs/database.md) and
  [interface design](docs/interface.md)
- [Design decisions](docs/design-decisions.md): the deep-dive challenge
- [Evaluation](docs/evaluation.md) and [known limitations](docs/limitations.md)
- [Engineering audit](docs/engineering_audit.md) and [remediation plan](docs/remediation_plan.md)
- [Deployment](docs/deployment.md) and [demonstration script](docs/demo_script.md)

## Use of AI tools

AI coding assistants were used extensively for implementation, research, review and
drafting, including the engineering audit. Behaviour described here is backed by the tests
and the generated evaluation report; anything not verified is listed as such.

The restaurant, menu and allergen data are fictional sample data.
