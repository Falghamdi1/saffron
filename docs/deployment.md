# Deployment

Supabase (auth and database), Gemini, and one Render web service built from the
`Dockerfile`. All have free tiers. Allow about 30 minutes.

Check current free-tier terms before relying on them: they change.

## 1. Supabase

1. Create a project and keep the database password.
2. **Authentication → Sign In / Providers → Email:** turn off *Confirm email*, so reviewers
   can register without a mailbox round trip.
3. From **Connect**, copy the **Session pooler** connection string (Render's free tier has
   no IPv6, so the direct connection will not work). Append `?sslmode=require`.
   Replace `[YOUR-PASSWORD]` including the square brackets.
4. From **Project Settings**, copy the project URL and the **publishable** (anon) key.
   If the project still uses a legacy HS256 JWT secret, copy that too.

Never use the secret/service-role key; the application does not need it.

## 2. Gemini

Create an API key in Google AI Studio. Check that the model in `GEMINI_MODEL` is available
to your key and note its daily limit.

Put the values in a local `.env` (see `.env.example`, `AUTH_MODE=supabase`) and verify
before deploying:

```powershell
cd backend
.\.venv\Scripts\python -m app.setup_db
.\.venv\Scripts\python -m evaluation.run --llm
```

The second command scores Gemini on the held-out phrasings and runs the scenarios with it
(about twelve minutes, roughly 100 model calls), then updates `docs/evaluation.md`. If it reports
failed model calls, fix that before deploying.

Then run the app against Supabase from your machine and check it, so database permissions and
token verification are proven before hosting is involved:

```powershell
.\.venv\Scripts\python -m uvicorn app.main:create_app --factory --port 8000
```

In a second terminal, set the `CHECK_*` variables from step 6 and run
`.\.venv\Scripts\python -m evaluation.live_check http://127.0.0.1:8000`.

## 3. GitHub

Create an empty repository, then:

```powershell
git remote add origin https://github.com/<you>/<repo>.git
git push -u origin main
```

Check that the CI workflow passes.

## 4. Render

1. **New → Blueprint**, select the repository (`render.yaml` is detected).
2. Enter `DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `GEMINI_API_KEY`, and
   `SUPABASE_JWT_SECRET` only for legacy-secret projects.
3. Deploy. The container applies the schema and loads the menu on start.

## 5. Keep it awake

In the GitHub repository, add an Actions **variable** `APP_URL` with the Render URL, and run
the *Keep alive* workflow once by hand.

A run every ten minutes is about 4,300 billed minutes a month. That is free for public
repositories but exceeds the free allowance of a private one: for a private repository,
disable the workflow and point an external uptime monitor at `/api/health` instead.

## 6. Verify the live application

Create two test accounts in the app (use addresses made for testing). Then:

```powershell
$env:CHECK_USER_A = "<first test email>"
$env:CHECK_PASSWORD_A = "<its password>"
$env:CHECK_USER_B = "<second test email>"
$env:CHECK_PASSWORD_B = "<its password>"
cd backend
.\.venv\Scripts\python -m evaluation.live_check https://<your-app>.onrender.com
```

All ten lines should read `PASS`, including `language model is in use`.

Also check by hand, on a phone and a computer:

- [ ] Register, state an allergy, sign out, sign in, start a new conversation: it applies.
- [ ] A second account sees none of it.
- [ ] The URL works in a private window.

## 7. Reviewer instructions

Include this with the submission:

> Open the URL (the first load may take up to a minute). Create an account with any email
> and a password of at least 8 characters; no confirmation email is sent. Create a second
> account in a private window to check that users are isolated.

If you would rather provide ready-made accounts, share their credentials through the
submission folder, not the repository.
