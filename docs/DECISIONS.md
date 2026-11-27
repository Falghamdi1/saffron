# Design decisions

## Why memory

The assistant's value on a second visit is entirely what it remembers. Memory is also where
the risk is: a lost allergy can harm someone, a guess stored as fact silently narrows what
they are offered, and a "today only" wish saved forever makes the product feel broken. These
are failures of *write rules*, which is why the work went there rather than into retrieval
or a smarter prompt.

Chosen over: integrations (hard to demonstrate honestly without a real POS), voice (large
effort, mostly vendor plumbing) and scale (no realistic load to measure).

## Decisions and their costs

**The model proposes, code decides.**
Safety rules are testable and do not change with the model. Cost: nuance the schema cannot
express is lost.

**Replies are composed from templates, not generated.**
No invented dishes or allergen claims, one model call per turn, identical behaviour in
tests. Cost: the voice is plainer and less flexible than a generated reply. I would revisit
this with a generator whose output is checked against the selected records.

**Relational memory, no vector store.**
Preferences are small, structured and need exact semantics (supersede, retract, confirm).
Cost: free-form facts that fit no category ("I usually order for four") are not kept.

**Asymmetric treatment of risk.**
Adding a restriction is easy; removing an allergy takes a deliberate click. A pending
allergy is avoided, a pending diet is not, because the harms differ. Cost: someone who is
only curious may see dishes withheld until they dismiss the suggestion.

**Dislikes are hard exclusions.**
Offering a dish with a stated dislike reads as not listening. Cost: fewer options. Asking
for that food by name lifts the dislike for that conversation.

**`may_contain` and unverified data exclude.**
For allergy sufferers the conservative answer is the only defensible one. Cost: some
probably-safe dishes are never offered.

**Rules as a second reader.**
They keep the app working during outages or quota exhaustion and add any clear allergy
statement the model misses. Cost: measured recall on unfamiliar phrasing is low (see the
evaluation), so the interface tells the user when only rules were used, and allergies can be
added directly in the preferences panel.

**Row Level Security from the backend, not a service key.**
Each transaction drops to `authenticated` with the verified user id. A forgotten `WHERE`
clause returns nothing foreign. Cost: the connecting role is still privileged; a dedicated
login role with only `authenticated` membership would be stronger.

**One service.**
FastAPI serves the client, so there is one deployment, one origin and no CORS. Cost: no
separate CDN, and free-tier sleep affects the whole application.

**No agent framework.**
The turn is a fixed five-step pipeline. A framework would hide the control flow that the
safety argument depends on.

## Left out on purpose

| Not built | Reason |
| --- | --- |
| Cart, ordering, payment | the brief is about choosing what to order |
| POS integration, menu admin | not the chosen challenge |
| Streaming replies | replies are short and composed instantly |
| Embedding search over past chats | structured memory answers the same questions reliably |
| Learning weights from behaviour | no real behaviour data to learn or validate from |
| Arabic | important for this market, but needs its own extraction and evaluation |
| Food photography | stock images would misrepresent fictional dishes |

## With more time

1. Score and tune Gemini extraction on a larger set written by other people.
2. Arabic input and a right-to-left interface.
3. Let the model resolve follow-ups ("yes", "the second one") using recent turns.
4. Preference expiry and re-confirmation for old inferred tastes.
5. A dedicated low-privilege database role and a shared rate limiter.
