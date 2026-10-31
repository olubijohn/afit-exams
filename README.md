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

3,395 questions in three papers, chosen with the buttons at the top of every page: **General Paper** (1,053, eight subjects), **Piston Engines** (557) and **Pressurised Airframe** (1,785, NCAA past papers plus the Module 11 bank in 13 topics). Each paper has its own home page, Continue, practice, question list and history, and the app remembers the last one used. `/piston` and `/pma` open that paper directly (`vercel.json` sends them to `index.html`); old links to a single subject such as `/law` open the paper it belongs to. Saved quizzes and progress from the old per-subject pages carry over.

The questions come from these sources:

- **General paper** (`GENERAL PAPER _240124_171633 (1).pdf`), 940 questions. Answers are the options printed in red or green, or highlighted. 19 items were left out: they had no options, needed a diagram, or had no marked answer.
- **Piston engines & systems** (`SLIDE ON PISTON AND SYSTEMS.pdf`), 557 questions, one per slide; "No." is the slide number minus one. Answers are the highlighted option, or the red one where a slide has no highlight. Statement questions ("1, 2 and 3") list the statements in the question; worked answers become the note shown after answering. Left out: 3 slides that give only the answer, and the break slides. On slide 37 two options were highlighted; d) is used, with a note. `tools/extract_piston_slides.py` is the extractor.
- **Pressurised metal airframe** (`pma`), 527 questions merged from `PRESSURIZED AIRFRAME  NCAA.pdf` (three papers, answers in red), `200+PRESSURISED AIRFRAME LICENSE EXAM.pdf` (answers highlighted) and the scanned `PMA 2019.pdf` (answers underlined, read page by page into `tools/pma/scan_*.json`). `PRESSURISED METAL AIRFRAME2018.doc` and `PMA 2019 STUDIES-1.doc` repeat the NCAA papers and were used only to check answers. Repeats are merged. Left out: 4 questions whose copies give different answers that couldn't be settled, questions with no marked answer, and a few with an unreadable or garbled stem. Scripts are in `tools/pma/` (`parse_pma_pdf.py`, `readdoc.py`, `merge_pma.py`, `export_pma.py`). The paper is now named **NCAA Past Papers** inside Pressurised Airframe.
- **October 2026 additions** (`tools/import2026/`, run `python -I merge.py`; it can be re-run):
  - `GENERAL PAPER.pdf`: 113 new questions. The other 70 repeat the existing general paper and the 3 that need a diagram are left out. Each new question is filed under the general subject whose existing questions it is most like.
  - `NCAA AIRFRAME.docx` (EASA Module 11 bank, answers and explanations): 1,254 questions in 13 topic subjects (`af-*`). Repeats inside the bank and questions already in the NCAA past papers are left out.
  - `AME PART 1.pdf` and `AME PART 2.pdf` (Quizlet): 457 parsed, almost all already in the bank; 4 new ones go into NCAA Past Papers.
  - `AIRFRAME QUESTION - JULY 2019.docx`: every clean question was already in the bank, so nothing new was added.
  - `PMA 2019 (1).pdf` is the same file as `PMA 2019.pdf`.

## Run locally

```sh
python -m http.server 8080   # subject pages (/piston) need the Vercel rewrite; locally use /#/ addresses
# open http://localhost:8080
```

## Deploy changes

```sh
# database (run once per new migration)
npx supabase db query --linked --project-ref npyxfreikuxuaroyvmcp -f supabase/migrations/0001_afit_schema.sql
# edge function
npx supabase functions deploy afit-account --project-ref npyxfreikuxuaroyvmcp --no-verify-jwt --use-api
```

The site is live at https://ncat-exams.vercel.app (Vercel, from the `main` branch of github.com/olubijohn/afit-exams), so pushing to `main` updates it.
