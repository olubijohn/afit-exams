-- Replies (with a snapshot of the message being answered) and editing your own messages.
alter table public.afit_messages
  add column if not exists reply_to   bigint references public.afit_messages(id) on delete set null,
  add column if not exists reply_name text,
  add column if not exists reply_snip text,
  add column if not exists edited_at  timestamptz;

grant insert (room, body, image, reply_to) on public.afit_messages to authenticated;
grant update (body) on public.afit_messages to authenticated;

drop policy if exists afit_messages_edit on public.afit_messages;
create policy afit_messages_edit on public.afit_messages for update to authenticated
  using (sender_id = auth.uid()) with check (sender_id = auth.uid());

create or replace function public.afit_messages_before() returns trigger
language plpgsql security definer set search_path = public as $$
declare n int;
begin
  new.sender_id := auth.uid();
  new.created_at := now();
  new.body := coalesce(new.body, '');
  new.edited_at := null;
  select full_name into new.sender_name from afit_profiles where id = auth.uid();
  if new.sender_name is null then raise exception 'Only NCAT Exams members can chat.' using errcode = '42501'; end if;
  select count(*) into n from afit_messages where sender_id = auth.uid() and created_at > now() - interval '10 seconds';
  if n >= 8 then raise exception 'You are sending messages too fast. Slow down a little.'; end if;
  new.reply_name := null; new.reply_snip := null;
  if new.reply_to is not null then
    select m.sender_name,
           case when btrim(m.body) <> '' then left(regexp_replace(m.body, '\s+', ' ', 'g'), 140) else 'Picture' end
      into new.reply_name, new.reply_snip
      from afit_messages m where m.id = new.reply_to and m.room = new.room;
    if not found then new.reply_to := null; end if;
  end if;
  return new;
end $$;

create or replace function public.afit_messages_edit() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if new.body is distinct from old.body then new.edited_at := now(); end if;
  return new;
end $$;
drop trigger if exists afit_messages_edit on public.afit_messages;
create trigger afit_messages_edit before update on public.afit_messages for each row execute function public.afit_messages_edit();
