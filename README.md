# NCAT Exams

Practice app for the NCAT general paper: 940 questions in 8 subjects, with instant right/wrong feedback, a live score, timed mock exams, saved history and a list of the questions you got wrong to go back over.

It's a static site (no build step). Accounts and results are stored in the **Commerce Cloud** Supabase project (`shopmate-offline`, ref `npyxfreikuxuaroyvmcp`), in tables prefixed `afit_`. Nothing else in that project is touched.

## How accounts work

1. **Create account**: the person enters their name and email. The `afit-account` edge function creates the login with a temporary password (`NCAT-XXXX-XXXX`) and emails it through SendGrid.
2. **First sign-in**: with the temporary password, they have to choose their own password before they can use the app.
3. **Forgot password**: emails a fresh temporary password. The same rule applies on the next sign-in. Requests are limited to one every two minutes per account.

## Layout

| Path | What it is |
| --- | --- |
| `index.html`, `assets/` | The app (plain JS, Supabase JS from a CDN) |
| `assets/config.js` | Supabase URL, the public anon key and the pass mark (75%) |
| `data/questions.json` | The question bank, extracted from `GENERAL PAPER _240124_171633 (1).pdf` |
| `supabase/migrations/0001_afit_schema.sql` | Tables, row-level security and functions |
| `supabase/functions/afit-account` | Sign-up and password-reset mailer |

## Question bank

Answers come from the marking in the source PDF (answers are in red or green, or highlighted). 19 items were left out: they had no options, needed a diagram, or had no marked answer. Notes printed under some questions in the PDF show up after you answer.

## Run locally

```sh
python -m http.server 8080
# open http://localhost:8080
```

## Deploy changes

```sh
# database (run once per new migration)
npx supabase db query --linked --project-ref npyxfreikuxuaroyvmcp -f supabase/migrations/0001_afit_schema.sql
# edge function
npx supabase functions deploy afit-account --project-ref npyxfreikuxuaroyvmcp --no-verify-jwt --use-api
```

The site is live at https://afit-exams.vercel.app (Vercel, from the `main` branch of github.com/olubijohn/afit-exams), so pushing to `main` updates it.
