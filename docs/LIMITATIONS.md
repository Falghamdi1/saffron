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

## Behaviour

- English only.
- Gemini can attribute someone else's taste to the user: "My colleague loves lamb" was saved
  as the user's own preference.
- A live call took about six seconds, so replies feel slow.
- The model sees one message at a time, so "yes", "that one" or "the second" are not
  understood. Confirmations use buttons.
- Replies are templated.
- Budget means price per dish, not for the whole order.
- Preferences are a fixed set of categories; other facts are not remembered.
- Reopened conversations show recommendations as they were then, even if preferences or the
  menu have since changed.
- Group dining is not modelled. Another person's allergy is applied to that chat only, and
  only for common phrasings.

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
