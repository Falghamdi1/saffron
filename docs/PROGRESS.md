# Progress log

## 2026-11-27

- Read the brief; wrote the requirements checklist.
- Built schema with Row Level Security, memory policy, recommender, API and chat pipeline.
- Built the React client; checked chat, preferences, menu, comparison and phone layout in a
  browser.
- Added end-to-end scenarios, a constraint sweep and held-out phrasings.
- Fixed from testing: missed "I might be vegetarian"; multi-word allergens not resolving
  ("sesame seeds"); phone header overflow.
- Added deployment configuration and a live smoke test, run locally only.

- Verified Gemini live. Fixed: a dropped price limit, a hedged statement stored as a
  dislike, an unknown dish not reported, and no retry on model overload.

- Set up the Supabase project and loaded the schema. The live smoke test passed with the
  app running locally: sign-in, remembered allergy, Gemini in use, isolation of two accounts.

- Pushed to GitHub. The first CI run showed that local mode rejected the Unix-socket
  database used on Linux and macOS; fixed, and the host check now also covers `?host=`
  overrides. Backend, frontend and image jobs then passed.

- Deployed to Render at https://saffron-ai-zrnt.onrender.com. The first deploys failed on missing variables
  and then on a newline pasted into `DATABASE_URL`; the app now trims such values. The live
  smoke test passed against the deployment.

Open: manual check on a phone, keep-alive variable, video, submission.
