# Video walkthrough outline (about 10 minutes)

Record against the deployed app. Use a fresh account.

| Time | Section | Show |
| --- | --- | --- |
| 0:00–0:40 | Problem | An assistant that forgets is useless; one that remembers wrongly is unsafe. |
| 0:40–3:30 | Baseline | see script below |
| 3:30–4:30 | Chosen challenge | Why memory, and what you did not pick (DECISIONS.md). |
| 4:30–7:30 | Technical deep dive | pipeline diagram, `policy.py`, `db.py`, `engine.py` |
| 7:30–8:30 | Scope and trade-offs | templated replies, no vector store, conservative exclusions |
| 8:30–9:40 | Validation | run `pytest`, open EVALUATION.md, show the weak result |
| 9:40–10:00 | Next steps | Arabic, follow-up resolution, larger independent evaluation |

## Baseline script

1. "Hi, I'm allergic to nuts and I love chicken." Point at the saved notes and side panel.
2. "What should I have for dinner under 60 riyals?" Point at reasons and exclusions.
3. New conversation: "What do you recommend?" The allergy applies without repeating it.
4. "I usually like mild food." Then "Today I want something spicy."
5. New conversation: it is back to mild.
6. "I'm not allergic to nuts anymore." Show that it asks, then **My preferences** and the
   history. Choose *Keep it*.
7. Second account in a private window: empty memory.

## Deep dive: points worth making

- **The invariant:** no model output can write memory or choose a dish.
- **One rule in code:** how `_retract` treats allergies differently.
- **One database detail:** why composite foreign keys are needed when RLS is on
  (foreign key checks bypass it).
- **One bug found by evaluation:** "sesame seeds" was stored as an unknown allergen and
  filtered nothing. How the held-out phrasings exposed it, and the fix.
- **One honest weakness:** rule-only recall, and what the product does about it.

## Prepare for the interview

Be able to explain without notes: the transaction in `handle_message`; what
`set local role authenticated` does; why the LLM call is outside the transaction; what
happens when two messages arrive at once; why a pending allergy and a pending diet behave
differently; what would change at 10,000 menu items.
