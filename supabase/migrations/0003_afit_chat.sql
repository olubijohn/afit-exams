-- Chat between signed-in NCAT Exams members: one room for everyone plus one-to-one rooms.
-- room = 'general' or 'dm:<uuid>:<uuid>' (the two ids sorted). Pictures are shrunk in the
-- browser and stored inline as base64 data URLs, so no file storage is used.

create or replace function public.afit_is_member() returns boolean
language sql security definer stable set search_path = public as $$
  select exists (select 1 from afit_profiles where id = auth.uid());
$$;
revoke all on function public.afit_is_member() from public, anon;
grant execute on function public.afit_is_member() to authenticated;

-- names of everyone in the app (never emails), for chat headers and lists
create or replace function public.afit_people() returns table (id uuid, full_name text)
language sql security definer stable set search_path = public as $$
  select p.id, p.full_name from afit_profiles p where public.afit_is_member();
$$;
revoke all on function public.afit_people() from public, anon;
grant execute on function public.afit_people() to authenticated;

create table if not exists public.afit_messages (
  id          bigint generated always as identity primary key,
  room        text not null check (room = 'general' or room ~ '^dm:[0-9a-f-]{36}:[0-9a-f-]{36}$'),
  sender_id   uuid not null default auth.uid() references auth.users(id) on delete cascade,
  sender_name text not null default '',
  body        text not null default '' check (char_length(body) <= 4000),
  image       text check (image is null or (char_length(image) <= 200000 and image ~ '^data:image/(png|jpeg|webp|gif);base64,')),
  created_at  timestamptz not null default now(),
  check (char_length(btrim(body)) > 0 or image is not null)
);
create index if not exists afit_messages_room_idx on public.afit_messages (room, created_at desc);
alter table public.afit_messages enable row level security;

drop policy if exists afit_messages_read on public.afit_messages;
create policy afit_messages_read on public.afit_messages for select to authenticated using (
  public.afit_is_member() and (room = 'general' or auth.uid()::text in (split_part(room, ':', 2), split_part(room, ':', 3))));
drop policy if exists afit_messages_send on public.afit_messages;
create policy afit_messages_send on public.afit_messages for insert to authenticated with check (
  sender_id = auth.uid() and public.afit_is_member()
  and (room = 'general' or auth.uid()::text in (split_part(room, ':', 2), split_part(room, ':', 3))));
drop policy if exists afit_messages_delete on public.afit_messages;
create policy afit_messages_delete on public.afit_messages for delete to authenticated using (sender_id = auth.uid());

revoke all on public.afit_messages from anon, authenticated;
grant select, delete on public.afit_messages to authenticated;
grant insert (room, body, image) on public.afit_messages to authenticated;

-- the sender's name comes from their profile (so nobody can post as someone else), and a simple flood limit
create or replace function public.afit_messages_before() returns trigger
language plpgsql security definer set search_path = public as $$
declare n int;
begin
  new.sender_id := auth.uid();
  new.created_at := now();
  new.body := coalesce(new.body, '');
  select full_name into new.sender_name from afit_profiles where id = auth.uid();
  if new.sender_name is null then raise exception 'Only NCAT Exams members can chat.' using errcode = '42501'; end if;
  select count(*) into n from afit_messages where sender_id = auth.uid() and created_at > now() - interval '10 seconds';
  if n >= 8 then raise exception 'You are sending messages too fast. Slow down a little.'; end if;
  return new;
end $$;
drop trigger if exists afit_messages_before on public.afit_messages;
create trigger afit_messages_before before insert on public.afit_messages for each row execute function public.afit_messages_before();

-- live updates
do $$ begin
  if not exists (select 1 from pg_publication_tables where pubname = 'supabase_realtime' and schemaname = 'public' and tablename = 'afit_messages') then
    alter publication supabase_realtime add table public.afit_messages;
  end if;
end $$;
