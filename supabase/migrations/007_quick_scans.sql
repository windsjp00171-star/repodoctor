-- 免登入秒檢：貼上 GitHub「公開」repo 的網址，不用登入就能跑一次規則掃描。
--
-- 設計（擋濫用、不碰私人 repo）：
--   - 沒登入的人碰不到這張表，只能呼叫兩個函式：request_quick_scan（申請）、quick_scan_status（看結果）
--   - 只接受 owner/repo 格式；worker 下載時不帶任何權限，私人 repo 根本下載不到
--   - 只跑規則掃描（不花 AI 的錢）
--   - 全站每天最多 100 次；同一個 repo 一小時內再送出，直接回上一次的結果
--   - 不記錄是誰申請的；結果保存 7 天（purge_quick_scans）

create table public.quick_scans (
  id              uuid primary key default gen_random_uuid(),
  full_name       text not null check (full_name ~ '^[A-Za-z0-9][A-Za-z0-9-]{0,38}/[A-Za-z0-9._-]{1,100}$'),
  status          text not null default 'queued' check (status in ('queued', 'running', 'done', 'failed')),
  score           int,
  category_scores jsonb,
  summary         jsonb,
  coverage        jsonb,
  meta            jsonb,
  findings        jsonb,
  error           text,
  created_at      timestamptz not null default now(),
  finished_at     timestamptz
);
create index quick_scans_name_idx on public.quick_scans (lower(full_name), created_at desc);
create index quick_scans_created_idx on public.quick_scans (created_at);

alter table public.quick_scans enable row level security;   -- 沒有任何 policy：只有 service_role（worker）讀寫得到
revoke all on public.quick_scans from anon, authenticated;
grant all on public.quick_scans to service_role;

-- 申請秒檢：回傳這次（或一小時內同一個 repo 上一次）的 id
create function public.request_quick_scan(repo text) returns uuid
language plpgsql security definer set search_path = '' as $$
declare
  name text := btrim(repo);
  existing uuid;
  new_id uuid;
begin
  if name !~ '^[A-Za-z0-9][A-Za-z0-9-]{0,38}/[A-Za-z0-9._-]{1,100}$' then
    raise exception 'invalid_repo' using errcode = '22023';
  end if;
  select id into existing from public.quick_scans
    where lower(full_name) = lower(name) and status <> 'failed' and created_at > now() - interval '1 hour'
    order by created_at desc limit 1;
  if existing is not null then
    return existing;
  end if;
  if (select count(*) from public.quick_scans where created_at > now() - interval '1 day') >= 100 then
    raise exception 'daily_limit' using errcode = '53400';
  end if;
  insert into public.quick_scans (full_name) values (name) returning id into new_id;
  return new_id;
end;
$$;

-- 看結果：只回傳報告要用的欄位
create function public.quick_scan_status(scan_id uuid)
returns table (id uuid, full_name text, status text, score int, category_scores jsonb, summary jsonb,
               coverage jsonb, meta jsonb, findings jsonb, error text, created_at timestamptz, finished_at timestamptz)
language sql stable security definer set search_path = '' as $$
  select q.id, q.full_name, q.status, q.score, q.category_scores, q.summary, q.coverage, q.meta, q.findings,
         q.error, q.created_at, q.finished_at
  from public.quick_scans q where q.id = scan_id;
$$;

-- worker 用：搶下一個待辦的秒檢
create function public.claim_next_quick_scan() returns setof public.quick_scans
language sql security definer set search_path = '' as $$
  update public.quick_scans q set status = 'running'
  where q.id = (select id from public.quick_scans where status = 'queued' order by created_at for update skip locked limit 1)
  returning q.*;
$$;

-- worker 用：秒檢結果只保存 7 天
create function public.purge_quick_scans(retention_days int default 7) returns int
language sql security definer set search_path = '' as $$
  with gone as (delete from public.quick_scans where created_at < now() - make_interval(days => retention_days) returning 1)
  select count(*)::int from gone;
$$;

revoke all on function public.request_quick_scan(text) from public;
revoke all on function public.quick_scan_status(uuid) from public;
revoke all on function public.claim_next_quick_scan() from public, anon, authenticated;
revoke all on function public.purge_quick_scans(int) from public, anon, authenticated;
grant execute on function public.request_quick_scan(text) to anon, authenticated;
grant execute on function public.quick_scan_status(uuid) to anon, authenticated;
grant execute on function public.claim_next_quick_scan() to service_role;
grant execute on function public.purge_quick_scans(int) to service_role;

-- 有人申請就叫醒 worker（沿用 002 的 kick_worker）
create trigger kick_worker_on_quick_scan after insert on public.quick_scans
  for each row execute function public.kick_worker();

-- 通知 Supabase 的資料庫 API 重新讀取資料表清單（不然新表、新函式要等快取更新才找得到）
notify pgrst, 'reload schema';
