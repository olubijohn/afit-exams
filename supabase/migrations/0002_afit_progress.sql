-- Where each person is up to when going through the paper in order.
-- { "c": { "<subject>": <questions covered> }, "last": <the quiz settings used last> }
alter table public.afit_profiles add column if not exists progress jsonb not null default '{}';
grant update (progress) on public.afit_profiles to authenticated;
