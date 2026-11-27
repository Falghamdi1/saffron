# Design decisions

The deep-dive challenge is **reliable long-term memory and personalization**.

## The problem

An ordering assistant's value on a second visit is entirely what it remembers. Memory is
also where the risk is:

- a lost allergy can harm someone;
- a guess stored as fact silently narrows what they are offered;
- a "today only" wish saved forever makes the product feel broken;
- a statement about a friend saved as the customer's own is memory that was never true.

All four are failures of *write rules*: what gets stored, with what certainty, for how long,
and about whom. That is why the work went there and not into retrieval or a larger prompt.

## Why this over the other directions

| Direction | Why not |
| --- | --- |
| Restaurant integrations | hard to demonstrate honestly without a real point-of-sale system |
| Voice | large effort, mostly vendor plumbing, and it would not make memory safer |
| Scalability | there is no realistic load to measure |
| User experience or evaluation alone | both matter, and are included as far as memory needs them |

## What was built

1. **Structured memory.** Typed records with status (`active`, `pending`, `superseded`,
   `retracted`), certainty, the sentence they came from, and an append-only history.
2. **A pure policy** that decides every change. The model only proposes.
3. **Attribution.** Statements about other people are not saved. Their allergies are
   enforced for that conversation.
4. **Temporary and persistent separation.** "Today" lives with the conversation.
5. **Hard filtering before ranking**, so preferences can never outweigh a restriction.
6. **Transparency.** The diner sees each record, where it came from and how it changed, and
   can confirm, reject or remove it.
7. **Evaluation** that can fail: held-out sentences, a constraint sweep with an independent
   checker, and end-to-end scenarios.

## Decisions and their costs

**The model proposes, code decides.**
Safety rules are testable and do not change with the model. Cost: nuance the schema cannot
express is lost.

**Replies are composed from templates, not generated.**
No invented dishes or allergen claims, one model call per turn, identical behaviour in
tests. Cost: the voice is plain and cannot discuss a dish beyond its record. A next step
would be generated wording whose facts are checked against the selected records.

**Relational memory, no vector store.**
Preferences are small, structured and need exact operations (supersede, retract, confirm).
Cost: facts that fit no category ("I usually order for four") are not kept.

**Asymmetric treatment of risk.**
Adding a restriction is easy; removing an allergy takes a deliberate click. A pending
allergy is avoided, a pending diet is not, because the harms differ. Cost: someone who is
only curious may see dishes withheld until they dismiss the suggestion.

**Dislikes are hard exclusions.**
Offering a dish with a stated dislike reads as not listening. Cost: fewer options. Asking
for that food by name lifts the dislike for that conversation.

**`may_contain` and incomplete data exclude.**
For someone with an allergy the conservative answer is the only defensible one. Cost: some
probably safe dishes are never offered.

**Whose statement is it: wording patterns, applied to both readers.**
The same check is applied to the model's output, using the whole clause its quote came
from. When it is unclear, an allergy is still enforced and the reply says it was not saved.
Cost: unusual phrasings are misattributed (see [limitations](limitations.md)).

**Rules as a second reader.**
They keep the app working when the model is unavailable or over quota, and add a clearly
stated allergy, spice limit or price limit the model missed. Cost: recall on unfamiliar
phrasing is low, so the interface says when only rules were used, and allergies can be added
directly in the preferences panel.

**Row Level Security from the backend, not a service key.**
Each transaction drops to `authenticated` with the verified user id. A forgotten `WHERE`
clause returns nothing foreign. Cost: the connecting role is still privileged; a dedicated
login role would be stronger.

**One service.**
FastAPI serves the client: one deployment, one origin, no CORS. Cost: no separate CDN, and
free-tier sleep affects the whole application.

**No agent framework.**
A turn is a fixed pipeline. A framework would hide the control flow that the safety
argument depends on.

**No automatic retry when the model is over quota.**
Retrying an exhausted free quota adds delay and uses more of it. The turn falls back to the
rules and says so. A paid tier is the real remedy.

## Validation, and what it changed

Measured results are in [evaluation.md](evaluation.md). The checks that found real defects:

- **Held-out sentences** showed "sesame seeds" stored as an unknown allergen, so tahini
  dishes were not excluded.
- **The first run with Gemini** showed a hedged sentence stored as a firm dislike.
- **An audit of the finished app** showed that "My wife is allergic to sesame" still
  recommended sesame dishes: another person's allergy had been treated as a dislike. This
  is now a separate, hard constraint with its own tests and live check.

The lesson from the last one: the tests covered the customer's own statements thoroughly,
and nobody had written a sentence about someone else.

## Interface

Set like a printed menu so dishes are easy to scan and compare, with allergen text more
prominent than other details. See [interface.md](interface.md).

## Left out on purpose

| Not built | Reason |
| --- | --- |
| Cart, ordering, payment | the brief is about choosing what to order |
| Point-of-sale integration, menu admin | not the chosen challenge |
| Streaming replies | replies are short and composed instantly |
| Search over past chats | structured memory answers the same questions reliably |
| Learning weights from behaviour | there is no behaviour data to learn or validate from |
| Arabic | important for this market, but needs its own extraction and evaluation |
| Food photography | stock images would misrepresent fictional dishes |

## With more time

1. A larger evaluation set written by other people, especially about attribution.
2. Arabic input and a right-to-left interface.
3. Follow-up resolution ("yes", "the second one") using recent turns.
4. Expiry and re-confirmation for old inferred tastes.
5. A low-privilege database role, a shared rate limiter and browser tests.
