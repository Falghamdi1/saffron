# Demonstration script (about 10 minutes)

## Before recording

- Open the live URL once, a minute early, so the free server is awake.
- Create two **new** accounts with made-up test addresses: *Diner A* and *Diner B*. Use a
  normal window for A and a private window for B.
- Keep `.env`, the Render and Supabase dashboards, and passwords off screen.
- The free model quota is 500 requests a day. Do not run the evaluation on the day you
  record. If a reply shows "I read this message with basic phrase matching", the quota is
  used up: record after it resets.
- Do one full practice run with a third account, then record with fresh ones.

## 0:00 Purpose (40 s)

"A restaurant assistant is only useful on the second visit if it remembers you, and only
safe if it remembers correctly. This one learns from ordinary conversation, recommends only
real menu items, and shows you everything it has stored."

## 0:40 First conversation and preference discovery (1 min 30)

Diner A. Open **My preferences** first to show it is empty, then go to **Order**.

| Type | Point out |
| --- | --- |
| `Hi! I love chicken, and I'm allergic to nuts.` | Notes show what was saved; the side panel updates; "nuts" became peanuts and tree nuts |
| `What should I have for dinner under 60 riyals?` | Cards with price, ingredients, allergens and "Why this dish"; the count of dishes left out; the safety notice |
| `I usually like mild food.` | A lasting spice preference |

Later replies in this chat repeat that the SAR 60 limit still applies. That is intended: say so
once, or start a new conversation to drop it.

## 2:10 Today only, comparison and unknown dishes (1 min)

| Type | Point out |
| --- | --- |
| `Today I want something spicy.` | A hot dish leads, and the saved preference stays mild (see the side panel) |
| `Compare Butter Chicken and Chicken Vindaloo` | "For you" row: butter chicken contains tree nuts |
| `Do you have sushi?` | It says sushi is not on the menu instead of inventing it |

## 3:10 Returning in a separate conversation (1 min)

Sign out, sign in again as Diner A, press **New conversation**.

| Type | Point out |
| --- | --- |
| `What do you recommend for dinner?` | Nothing about nuts was repeated, yet the allergy applies; mild chicken dishes lead |

## 4:10 Corrections and caution (1 min 20)

| Type | Point out |
| --- | --- |
| `Actually, I don't like chicken anymore.` | Updated, not duplicated; chicken disappears |
| `I'm not allergic to nuts anymore.` | It keeps both nut allergies and asks. Press **Keep it** on each |
| `I think I might be vegetarian.` | Asked, not assumed |

Open **My preferences**: each record has its source sentence, and "How it changed" shows
the replaced taste.

## 5:30 Other people (50 s)

New conversation.

| Type | Point out |
| --- | --- |
| `My wife is allergic to sesame. What mains can she have?` | Sesame dishes are excluded for this chat, and **My preferences** is unchanged |

"The finished app got this wrong. An audit showed it only matched ingredient names for
other people, so it still offered sesame dishes. It is now a hard constraint with tests and
a live check."

Show Diner B's empty preference panel: accounts are isolated.

## Optional: one memory, two languages (30 s)

Only if rehearsed. Switch to العربية, start a new conversation and type
`وش تنصحني للعشا؟`: the allergy saved in English still applies. Take the time from the
challenge section.

## 6:20 The challenge and the implementation (2 min)

Say why memory, and what was not chosen ([design-decisions.md](design-decisions.md)).

Show, in this order:

1. The diagram in [architecture.md](architecture.md): the model proposes, code decides.
2. `backend/app/memory/policy.py`: `_retract`, where chat cannot remove an allergy.
3. `backend/app/understanding/service.py`: `_reconcile`, the safeguards on model output.
4. `backend/app/db.py`: `set local role authenticated`.
5. `backend/app/recommendation/engine.py`: `violations` runs before any ranking.

## 8:20 Evidence (1 min)

- Run `.\.venv\Scripts\python -m pytest` (a few seconds).
- Open [evaluation.md](evaluation.md): scenarios, the constraint sweep, then the weak
  result: how much the rule-based fallback misses without the model.
- Mention one failure the evaluation caught: "sesame seeds" stored as an unknown allergen.

## 9:20 Trade-offs and next steps (40 s)

Templated replies, no vector store, conservative allergen exclusions. Next: a larger
evaluation by other people, Arabic, and follow-up questions.

Say that AI tools were used for development and research assistance.

## Be ready to explain without notes

- What happens inside `handle_message`, and why the model call is outside the transaction.
- What `set local role authenticated` does, and why composite foreign keys are still needed.
- What happens when two messages from one diner arrive at once.
- Why a pending allergy is enforced but a pending diet is not.
- How an allergy mentioned for someone else is told apart from the diner's own, and where
  that fails.
- What would change with 10,000 menu items.
