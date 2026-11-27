# Requirements checklist

Source: the Foodics AI Engineer take-home assignment. Test files are under `backend/`.

Status: **Done** is implemented and tested locally. **Pending** needs an external account,
key or recording.

## Baseline

| Requirement | Component | Evidence | Status |
| --- | --- | --- | --- |
| 2.1 Natural preference discovery, no questionnaire | `app/understanding/` | `tests/test_understanding.py` | Done; live Gemini path pending a key |
| 2.2 Recommendations from preferences, restrictions and request | `app/recommendation/engine.py` | `tests/test_recommendation.py`, quality scenarios | Done |
| 2.2 No invented dishes, prices or ingredients | `app/chat/reply.py` composes from records | scenario `nonexistent_dish` | Done |
| 2.3 Persistent memory across conversations | `app/memory/` | scenarios `persistence_across_sessions`, `persistence_across_restart` | Done |
| 2.4 Corrections and changing preferences | `app/memory/policy.py` | `tests/test_memory_policy.py`, update scenarios | Done |
| 2.5 Returning users, isolation | `app/auth.py`, `app/db.py`, RLS | `tests/test_auth.py`, `test_row_level_security_blocks_unfiltered_queries` | Done |
| 2.6 Deployed, usable interface | `frontend/`, `Dockerfile`, `render.yaml` | browser walkthrough (local) | **Pending deployment** |

## Menu

| Requirement | Evidence | Status |
| --- | --- | --- |
| At least 12 items across 3 categories | 24 items across 4: `test_menu_meets_the_brief` | Done |
| Different prices and spice levels | SAR 18–95, spice 0–3 | Done |
| Vegetarian and non-vegetarian | `diets` field | Done |
| Explicit ingredients and allergens | `allergens`, `may_contain`, `allergen_info_complete` | Done |
| Overlapping items for comparison | e.g. two kabsas, four curries | Done |
| Labels consistent with ingredients | `test_menu_labels_are_consistent_with_ingredients` | Done |

## Chosen challenge: memory and personalization

| Aspect to demonstrate | Where |
| --- | --- |
| Problem and why it matters | [DECISIONS.md](DECISIONS.md#why-memory) |
| Prioritization, scope and trade-offs | [DECISIONS.md](DECISIONS.md) |
| Implementation | [ARCHITECTURE.md](ARCHITECTURE.md#memory) |
| Validation | [EVALUATION.md](EVALUATION.md) |

## Deliverables

| Deliverable | Status |
| --- | --- |
| 6.1 Deployed application URL and test instructions | **Pending**: [DEPLOYMENT.md](DEPLOYMENT.md) |
| 6.2 Repository with README, architecture, decisions, setup, limitations; no secrets | Done locally; **pending push** |
| 6.3 Video, 8–12 minutes | **Pending**: [VIDEO_WALKTHROUGH.md](VIDEO_WALKTHROUGH.md) |
| 6.4 Google Drive folder with URL, repository, video and access notes | **Pending** |

## Timeline

72 consecutive hours from when HR sends the assignment; suggested effort 8–12 hours.
Confirm the exact deadline in the HR message.

## Evaluation criteria and where they show

| They value | Evidence |
| --- | --- |
| Working software | runs with no accounts in local mode |
| Judgment over complexity | one service, one database, no agent framework or vector store |
| Thoughtful scoping | "Left out" table in DECISIONS.md |
| Demonstrated results | generated evaluation report, including weak results |
| Clear ownership | design decisions with their costs |
