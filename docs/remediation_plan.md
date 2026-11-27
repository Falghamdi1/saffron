# Remediation plan

Based on [engineering_audit.md](engineering_audit.md). The priority order is: assignment
compliance and safety first, then correctness, reliability, user experience and
maintainability. Every step adds tests before it changes behaviour and ends with the full
test suite passing. Nothing here adds infrastructure.

## Phase 1: before submission

| # | Finding | Change | Files | Tests | Estimate |
| --- | --- | --- | --- | --- | --- |
| 1 | C1 | Add `allergies` to `RequestConstraints` for other diners at the table. Carry it across turns in `context.merge`, and merge it into the profile's hard allergy set in `build_profile`, so tags, "may contain", incomplete data and the safety notice all apply. Rules: the SOMEONE_ELSE branch fills it instead of `avoid`. Gemini: add the field to the instruction and schema | `schemas.py`, `chat/context.py`, `recommendation/engine.py`, `understanding/rules.py`, `understanding/llm.py` | Wife/sesame/mains and friend/peanut/lamb as scenarios; extend the constraint sweep with conversation allergies | 1.5 h |
| 2 | H1 | One attribution check, `rules.about_someone_else(text)`, covering "my son/wife/…", "someone with", "for a guest". In `_reconcile`, persistent candidates whose evidence is third-person are dropped; their allergies go to the request list from step 1. Rules use the same function | `understanding/rules.py`, `understanding/service.py` | Unit tests for both engines (mocked model output); add 4–6 third-person sentences to a **new** held-out file, and do not tune on it | 1 h |
| 3 | H2 | In `_reconcile`, restore the rules' spice preference when the model returned none (same pattern as price). In `normalize`, drop like/dislike values that are spice words | `understanding/service.py`, `memory/policy.py` | "I can't handle very spicy food" with mocked "dislike very spicy food" and "retract spice=hot" outputs | 30 min |
| 4 | H3 | Add mild patterns: "too spicy", "nothing … spicy", "sensitive to heat" | `understanding/rules.py` | Parametrised rule tests | 20 min |
| 5 | M1 | Do not carry `wants` from dish-question and compare turns; drop wants that name a menu dish once it has been answered | `chat/context.py`, `chat/service.py` | Pistachio ice cream, then "Recommend a dessert" | 30 min |
| 6 | M2 | `context.clean` strips generic nouns ("dish", "dishes", "food", "meal", "option") from wants and avoid | `chat/context.py` | "lamb dish" → lamb dishes | 15 min |
| 7 | Verify | Run `pytest`, `evaluation.run` and `evaluation.run --llm`, reporting the new numbers as measured, including any regressions. Deploy only with the owner's approval, then run `live_check` and the audit probes against the deployment | — | — | 45 min, mostly waiting |
| 8 | L1 | Update LIMITATIONS (latency, third-person handling, what is still unverified), EVALUATION commentary and PROGRESS | `docs/` | — | 20 min |
| 9 | M3 | Owner: set `APP_URL` in GitHub Actions variables and run *Keep alive* once | GitHub settings | Health check while warm | 5 min |

Phase 1 total: about 5–6 hours including evaluation runs.

## Phase 2: needs a decision, or worth doing if time allows

| # | Finding | Change | Note |
| --- | --- | --- | --- |
| 10 | H4 | Retry once on HTTP 429, honouring `Retry-After` within the existing 12 s budget. Add a global per-minute limit next to the per-user one | Small code change. Whether to also use a paid key or a second model is the owner's call (cost versus reviewer experience) |
| 11 | M4 | Accept a model-proposed `relaxed_diets` entry only if the diet is named in the message | 15 min with a test |
| 12 | L5 | When a carried-over budget or diet removes every match for a new request, say so in the reply | Template change |
| 13 | Measurement | Log the engine per turn (`gemini` or `fallback`) as a counter, so the fallback rate can be reported | One log line; no message text |

## Phase 3: low priority

- L2: a Content-Security-Policy header for the static client (`default-src 'self'`, plus
  the Supabase origin for `connect-src`). It needs care so it does not break the
  supabase-js client.
- L3: in the Supabase dashboard, set the minimum password length to 8 to match the UI,
  and consider CAPTCHA or email confirmation if the URL is shared widely.
- L4: upsert the profile only on first sign-in, or cache known ids per process.
- L6: a few component tests for the sign-in and memory panel flows.

## Deliberately not recommended

- An agent framework, vector store or embedding-based memory. The memory is a few dozen
  typed records per user; structured SQL with history is simpler and easier to audit.
- Letting the model write reply text. Templated replies are why nothing on the menu can be
  invented.
- Replacing the rule-based extractor with more regular expressions to chase recall. It
  should stay a safety net for allergies and price limits; recall comes from the model.
- New infrastructure (queues, Redis, separate services). The measured load does not need it.

## Implementation notes

- Order: H3 before H2, so restoring the rules' spice reading does not import the
  "too spicy" bug. Restore only when the model produced no spice assertion.
- H1: test the message clause that contains the evidence (`rules.clauses`), not only the
  evidence string, because the model may quote just "allergic to peanuts".
- C1: conversation allergies must join the same set that `violations`, `safety_notice`
  and the ranking reasons read. `_unknown_dishes` compares the request with an empty one,
  so it must ignore the new field. M1 must not stop table allergies carrying across turns.
- After the fixes, add "Status after remediation" to the audit report, so the public
  repository does not show an unresolved critical finding next to a live URL.

## Definition of done for Phase 1

- Every C and H finding has a regression test that failed before the change.
- The audit probes in section 5 of the audit report produce safe, correctly attributed results.
- The evaluation report is regenerated with measured numbers, including any regressions.
- The deployment passes the live check after an approved redeploy.
