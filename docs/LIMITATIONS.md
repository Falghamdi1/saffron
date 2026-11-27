# Known limitations

## Not yet verified

- The deployed application passed the live smoke test; it has not been checked by hand on a
  phone, and it has not been load tested.
- The automated tests use local PostgreSQL 16 with a shim for Supabase's `auth` schema and a
  locally generated signing key, not a Supabase project.
- Gemini results come from single live runs on one day. Model output varies between runs.

## Safety

- Menu and allergen data are fictional. The system cannot rule out cross-contact and says so.
- Without Gemini, many natural phrasings of an allergy are missed (see the evaluation).
  Do not run it for real diners in rules-only mode.
- Even with a model, an allergy can be misread. The preferences panel is the check.
- An allergen outside the tracked list is only matched against ingredient names.
- Whether a statement is about the customer or someone else is decided by wording patterns.
  Allergies mentioned for others are enforced for that chat but not remembered, and:
  - ways of agreeing such as "so do I", "neither can I" or "same here" are not recognised,
    so a shared allergy phrased that way is not saved to the customer's profile;
  - without Gemini, indirect phrasings ("sesame makes them very ill") are not caught at all.
- Without Gemini, some diet and spice changes are missed ("I've become vegetarian",
  "I can handle medium spice now").

## Behaviour

- English only.
- Turns measured during the audit took about 0.7 s at the median and 1.1 s at most,
  including some that fell back to rules. Earlier single calls took several seconds.
- The model sees one message at a time, so "yes", "that one" or "the second" are not
  understood. Confirmations use buttons.
- Replies are templated.
- Budget means price per dish, not for the whole order.
- Preferences are a fixed set of categories; other facts are not remembered.
- Reopened conversations show recommendations as they were then, even if preferences or the
  menu have since changed.
- Group dining is only partly modelled. Another person's allergy is a hard filter for the rest
  of that chat (including "may contain" and incomplete data) and cannot be lifted except by
  starting a new chat. Their diet and tastes are not tracked.

## Engineering

- The rate limiter is per process and resets on restart.
- The backend connects with a privileged database role and drops privileges per transaction.
- No account deletion, data export or conversation deletion in the interface.
- History grows without pruning.
- The frontend has no automated tests; it was checked by hand in a desktop and phone viewport.
- Local mode on Windows: force-killing the server can leave PostgreSQL running; the next
  start may pause while it recovers. Local sessions end when the server restarts.

## Hosting

- Free tiers sleep or pause when idle. A first request can take about a minute. The
  keep-alive workflow reduces this but scheduled runs are not guaranteed.
- Free model quotas can run out; the app then falls back to rules.

This is a take-home submission, not a production system.
