# Final submission checklist

Requirements are taken from the Foodics AI Engineer take-home assignment. Test names refer
to files under `backend/`.

**Statuses**

- **Verified:** checked on the current code, by the method shown.
- **Partially verified:** checked only in part, or on an earlier version, or not on the live
  site.
- **Not implemented:** the work or deliverable does not exist yet.
- **Not verified:** exists but has not been checked.

"Scenarios" means `evaluation/scenarios.py` ([evaluation.md](evaluation.md)): 30 of 30 pass
with rules. With Gemini the last complete run passed 29 of 30, the failure being a memory
error on the test machine; the rerun was cut short by the daily quota. The live check was last run by the project owner against
commit `6c66bb1`; later changes are **not yet deployed**.

## Part 1: baseline

| Requirement | Implementation | Verification | Status |
| --- | --- | --- | --- |
| 2.1 Natural conversation to learn favourites, diets, dislikes, budget | `app/understanding/`, chat screen | `tests/test_understanding.py`; held-out phrasings | Partially verified: some phrasings are missed |
| 2.1 No predefined questionnaire | chat only; the preferences panel is optional | interface check | Verified |
| 2.2 Recommendations from preferences, restrictions and request | `app/recommendation/engine.py`, dish entries | `tests/test_recommendation.py`; scenarios; constraint sweep | Verified |
| 2.2 No invented dishes, ingredients or prices | `app/chat/reply.py` builds replies from menu records | scenarios "Every dish shown is exactly the menu record" and "does not exist" | Verified |
| 2.3 Memory persists across conversations | `app/memory/`, PostgreSQL | scenarios; new application instance; live check | Verified |
| 2.3 Memory influences recommendations | `build_profile` | quality and memory scenarios | Verified |
| 2.4 Corrections and changing preferences | `app/memory/policy.py`, preferences screen | `tests/test_memory_policy.py`; update scenarios | Verified |
| 2.5 Returning users are identified | Supabase Auth, `app/auth.py` | `tests/test_auth.py`; live check | Verified |
| 2.5 Users' memories are isolated | Row Level Security, `app/db.py` | isolation scenarios; `tests/test_api.py`; live check | Verified |
| 2.6 Deployed application the team can use | Render, <https://saffron-ai-zrnt.onrender.com> | live check on `6c66bb1`; sign-in page loaded in a fresh browser tab | Partially verified: the current code is not deployed |

## Menu

| Requirement | Implementation | Verification | Status |
| --- | --- | --- | --- |
| At least 12 items in 3 categories | 24 items in 4 (`backend/data/menu.json`) | `test_menu_meets_the_brief` | Verified |
| Different prices and spice levels | SAR 18 to 95, spice 0 to 3 | same test | Verified |
| Vegetarian and non-vegetarian | `diets` field | same test | Verified |
| Explicit ingredients and allergens | `ingredients`, `allergens`, `may_contain`, completeness flag | `test_menu_labels_are_consistent_with_ingredients` | Verified |
| Overlapping items to compare | two kabsas, several curries and starters | comparison scenario; comparison screen | Verified |

## Part 2: chosen challenge (memory and personalization)

| Requirement | Where | Verification | Status |
| --- | --- | --- | --- |
| Problem identification | [design-decisions.md](design-decisions.md) | document review | Verified |
| Prioritisation | same | document review | Verified |
| Scoping and trade-offs, including what was left out | same | document review | Verified |
| Execution | `app/understanding/`, `app/memory/` | tests and scenarios | Verified |
| Validation that it works or improves the system | [evaluation.md](evaluation.md) | held-out sentences, sweep, scenarios | Partially verified: no independent test authors and no before/after user study |

## Deliverables

| Requirement | Evidence | Status |
| --- | --- | --- |
| 6.1 Working URL, accessible to reviewers | URL in the [README](../README.md) | Partially verified: current code not deployed |
| 6.1 Supports testing the baseline and the deep dive | "Try it" table in the README | Partially verified: as above |
| 6.1 Remains available during evaluation | keep-alive workflow | Not verified: `APP_URL` is not set, so it has never run; free tiers sleep |
| 6.1 Test instructions or credentials | self-service sign-up described in the README | Partially verified: sign-up was last used before these changes |
| 6.2 Repository | <https://github.com/Falghamdi1/saffron> (public) | Verified |
| 6.2 README: run locally, architecture, decisions, setup, limitations | [README](../README.md) | Verified: steps followed in a clean copy of the files |
| 6.2 No keys or credentials committed | history searched for the values in `.env` | Verified |
| 6.3 Video, 8 to 12 minutes | script in [demo_script.md](demo_script.md) | Not implemented |
| 6.4 Google Drive folder with URL, repository, video and access notes | — | Not implemented |
| 6.4 Links and permissions checked before submitting | — | Not verified |

## Video coverage required by 6.3

| Topic | In the script | Status |
| --- | --- | --- |
| Baseline: recommendations, memory across conversations, personalisation, updating preferences | 0:40 to 5:30 | Not implemented (not recorded) |
| Chosen challenge: what and why | 6:20 | Not implemented (not recorded) |
| Technical deep dive | 6:20 to 8:20 | Not implemented (not recorded) |
| Scope and trade-offs, alternatives, what next | 9:20 | Not implemented (not recorded) |
| Results and validation | 8:20 | Not implemented (not recorded) |

## Interface quality

| Check | Method | Status |
| --- | --- | --- |
| Phone, tablet and desktop widths | screenshots in an emulated viewport, local mode | Partially verified: no real device |
| Keyboard use, focus, back button | tried in the browser | Partially verified: no screen reader |
| Text and control contrast (WCAG AA) | computed from the colour tokens | Verified |
| Loading, empty and error states | code review; some seen in the browser | Partially verified |

## Before submitting

1. Approve the deploy of the current code, then run the live check (10 `PASS` lines).
2. In a private window, create a new account on the live site, state an allergy, sign out,
   sign in, start a new conversation and confirm it applies. Try the sesame sentence about
   another person.
3. Check the site on a real phone.
4. Set the `APP_URL` repository variable and run **Keep alive** once.
5. Record the video and upload it to the Drive folder with the URL, repository link and
   access notes.
6. Open every link from a signed-out browser.
7. Confirm the deadline in HR's message.
