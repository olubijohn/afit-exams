-- NCAT Exams on the Commerce Cloud Supabase project (shopmate-offline).
-- Everything lives in public.afit_* so it never touches Shopmate's tables.
-- Accounts are Supabase Auth users; afit_profiles marks which of them belong to NCAT Exams.

create table if not exists public.afit_profiles (
  id                   uuid primary key references auth.users(id) on delete cascade,
  email                text not null unique,
  full_name            text not null default '',
  must_change_password boolean not null default false,
  -- true when NCAT Exams created the login (so it may issue temporary passwords for it);
  -- false when someone signed in with a login that already existed on the project
  managed              boolean not null default false,
  temp_issued_at       timestamptz,
  created_at           timestamptz not null default now(),
  last_seen_at         timestamptz
);
alter table public.afit_profiles enable row level security;

drop policy if exists afit_profiles_read on public.afit_profiles;
create policy afit_profiles_read on public.afit_profiles for select to authenticated using (id = auth.uid());
drop policy if exists afit_profiles_insert on public.afit_profiles;
create policy afit_profiles_insert on public.afit_profiles for insert to authenticated
  with check (id = auth.uid() and managed = false and must_change_password = false and temp_issued_at is null);
drop policy if exists afit_profiles_update on public.afit_profiles;
create policy afit_profiles_update on public.afit_profiles for update to authenticated using (id = auth.uid()) with check (id = auth.uid());

revoke all on public.afit_profiles from anon, authenticated;
grant select on public.afit_profiles to authenticated;
grant insert (id, email, full_name) on public.afit_profiles to authenticated;
grant update (full_name, must_change_password, last_seen_at) on public.afit_profiles to authenticated;

-- people may only clear the "must change password" flag, never set it
create or replace function public.afit_profiles_guard() returns trigger language plpgsql as $$
begin
  if auth.role() = 'authenticated' and new.must_change_password and not old.must_change_password then
    new.must_change_password := old.must_change_password;
  end if;
  return new;
end $$;
drop trigger if exists afit_profiles_guard on public.afit_profiles;
create trigger afit_profiles_guard before update on public.afit_profiles for each row execute function public.afit_profiles_guard();


create table if not exists public.afit_attempts (
  id           uuid primary key default gen_random_uuid(),
  user_id      uuid not null default auth.uid() references auth.users(id) on delete cascade,
  client_id    text,
  mode         text not null check (mode in ('practice', 'timed', 'review')),
  title        text not null,
  subjects     text[] not null default '{}',
  total        int not null check (total > 0),
  answered     int not null check (answered >= 0),
  correct      int not null check (correct >= 0),
  score_pct    numeric(5,2) not null,
  duration_sec int not null default 0,
  answers      jsonb not null default '[]',
  created_at   timestamptz not null default now(),
  unique (user_id, client_id)
);
create index if not exists afit_attempts_user_idx on public.afit_attempts (user_id, created_at desc);
alter table public.afit_attempts enable row level security;

drop policy if exists afit_attempts_own on public.afit_attempts;
create policy afit_attempts_own on public.afit_attempts for all to authenticated
  using (user_id = auth.uid()) with check (user_id = auth.uid());
revoke all on public.afit_attempts from anon, authenticated;
grant select, insert, delete on public.afit_attempts to authenticated;


-- one row per person per question: drives "review mistakes" and subject mastery
create table if not exists public.afit_question_stats (
  user_id      uuid not null default auth.uid() references auth.users(id) on delete cascade,
  question_id  text not null,
  subject      text not null,
  seen         int not null default 0,
  correct      int not null default 0,
  last_correct boolean not null,
  updated_at   timestamptz not null default now(),
  primary key (user_id, question_id)
);
alter table public.afit_question_stats enable row level security;

drop policy if exists afit_stats_own on public.afit_question_stats;
create policy afit_stats_own on public.afit_question_stats for all to authenticated
  using (user_id = auth.uid()) with check (user_id = auth.uid());
revoke all on public.afit_question_stats from anon, authenticated;
grant select, insert, update, delete on public.afit_question_stats to authenticated;

-- p_items: [{ "q": "law-1", "s": "law", "ok": true }, ...]
create or replace function public.afit_record_answers(p_items jsonb) returns void
language sql security invoker set search_path = public as $$
  insert into afit_question_stats as t (user_id, question_id, subject, seen, correct, last_correct, updated_at)
  select auth.uid(), i->>'q', i->>'s', 1, case when (i->>'ok')::boolean then 1 else 0 end, (i->>'ok')::boolean, now()
  from jsonb_array_elements(p_items) i
  where auth.uid() is not null and coalesce(i->>'q', '') <> ''
  on conflict (user_id, question_id) do update
    set seen = t.seen + 1, correct = t.correct + excluded.correct, last_correct = excluded.last_correct, updated_at = now();
$$;
revoke all on function public.afit_record_answers(jsonb) from public, anon;
grant execute on function public.afit_record_answers(jsonb) to authenticated;


-- top learners over the last 30 days; names only (first name + initial), no emails
create or replace function public.afit_leaderboard() returns table (name text, attempts bigint, answered bigint, accuracy numeric, is_me boolean)
language sql security definer stable set search_path = public as $$
  select
    trim(split_part(p.full_name, ' ', 1) || coalesce(' ' || nullif(left(split_part(p.full_name, ' ', 2), 1), '') || '.', '')),
    count(*), sum(a.answered), round(100.0 * sum(a.correct) / nullif(sum(a.answered), 0), 1), p.id = auth.uid()
  from afit_attempts a join afit_profiles p on p.id = a.user_id
  where a.created_at > now() - interval '30 days' and a.answered > 0
  group by p.id, p.full_name
  having sum(a.answered) >= 20
  order by 4 desc, 3 desc
  limit 10;
$$;
revoke all on function public.afit_leaderboard() from public, anon;
grant execute on function public.afit_leaderboard() to authenticated;
