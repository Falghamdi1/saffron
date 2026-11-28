# Known limitations

This is a take-home submission, not a production system.

## Safety

- Menu and allergen data are fictional. The system cannot rule out cross-contact and says so.
- Without Gemini, many natural phrasings of an allergy are missed (see
  [evaluation.md](evaluation.md)). Do not run it for real diners in rules-only mode.
- Even with a model, an allergy can be misread. The preferences panel is the check.
- An allergen outside the tracked list is only matched against ingredient names.
- Whether a statement is about the customer or someone else is decided by wording patterns.
  Allergies mentioned for others are enforced for that chat but not remembered, and:
  - ways of agreeing such as "so do I", "neither can I" or "same here" are not recognised,
    so a shared allergy phrased that way is not saved to the customer's profile;
  - without Gemini, indirect phrasings ("sesame makes them very ill") are not caught.

## Behaviour

- English and Arabic only. Arabic is partially verified:
  - without Gemini, only direct statements about allergies, diets, spice, budget and common
    foods are read, mostly in Modern Standard and Gulf wording;
  - without Gemini, an Arabic question about a dish that is not served is not recognised;
  - with Gemini, only a one-off set of 12 Arabic messages has been tried;
  - with Gemini, asking in Arabic for a dish that is not served may not say so;
  - a rare allergen can be recorded twice, once translated and once as unidentified, which
    blocks suggestions until one record is resolved;
  - the Arabic wording and menu text have not been reviewed by a second reader;
  - history reasons and some server error messages are shown in English or generically.
- Without Gemini, only common wordings of a diet or spice change are recognised.
- The model sees one message at a time, so "yes", "that one" or "the second" are not
  understood. Confirmations use buttons.
- Replies are templated.
- Budget means price per dish, not for the whole order.
- Preferences are a fixed set of categories; other facts are not remembered.
- Spice, likes and cuisine rank dishes; they do not exclude them.
- A course or price mentioned earlier in a chat stays in force for that chat.
- Reopened conversations show recommendations as they were then, even if preferences or the
  menu have since changed.
- Group dining is only partly modelled. Another person's allergy is a hard filter for the
  rest of that chat and can only be lifted by starting a new one. Their diet and tastes are
  not tracked.
- Reloading the page opens a new chat; earlier ones are in the history list.

## Engineering and security

- The free Gemini quota (500 requests a day for this model when measured) is shared by
  everyone using the deployment and by evaluation runs with the same key. Each message uses
  one. When it runs out, turns fall back to the rules until it resets. There is no retry and
  no global limit.
- The rate limiter is per user, per process, and resets on restart.
- Sign-up is open without email confirmation, so reviewers can register. The interface
  requires eight characters; the server-side minimum is a Supabase setting that has not
  been checked.
- No Content-Security-Policy header. The Supabase session is kept in browser storage, as
  its library does by default.
- The backend connects with a privileged database role and drops privileges per
  transaction.
- No account deletion, data export or conversation deletion in the interface.
- History grows without pruning.
- The frontend has no automated tests.
- Local mode on Windows: force-killing the server can leave PostgreSQL running or in
  recovery; the next start may fail once or pause. Local sessions end when the server
  restarts.

## Hosting

- Free tiers sleep or pause when idle. A first request can take about a minute. The
  keep-alive workflow reduces this once enabled, and scheduled runs are not guaranteed.
- The application has not been load tested.
