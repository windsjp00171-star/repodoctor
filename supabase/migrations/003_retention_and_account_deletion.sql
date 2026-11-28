-- 資料保存期限與帳號刪除（隱私權政策承諾的兩件事，用程式保證）
--
-- 1. 健檢細節保存 90 天：findings（檔名、行號、程式片段、修復指令）超過 90 天自動刪除，
--    scans 只留分數與統計。由 worker 每次執行時呼叫 purge_expired_findings()。
-- 2. 刪除帳號：使用者在網站按「刪除我的所有資料」→ profiles.delete_requested_at 填上時間
--    → worker 用管理權限刪除 auth.users（profiles、installations、repos、scans、findings 全部連帶刪除）。
--    網站沒有管理權限，所以「刪帳號」只能由 worker 執行。

create index if not exists findings_created_idx on public.findings (created_at);

create function public.purge_expired_findings(retention_days int default 90) returns int
language sql security definer set search_path = '' as $$
  with gone as (
    delete from public.findings where created_at < now() - make_interval(days => retention_days) returning 1
  )
  select count(*)::int from gone;
$$;
revoke all on function public.purge_expired_findings(int) from public, anon, authenticated;
grant execute on function public.purge_expired_findings(int) to service_role;

alter table public.profiles add column if not exists delete_requested_at timestamptz;
grant update (delete_requested_at) on public.profiles to authenticated;

-- 有人申請刪除時立刻叫醒 worker（沿用 002 的 kick_worker，沒放 token 時什麼都不做，排程照樣會處理）
create trigger kick_worker_on_delete_request
  after update of delete_requested_at on public.profiles
  for each row when (new.delete_requested_at is not null and old.delete_requested_at is null)
  execute function public.kick_worker();

-- 通知 Supabase 的資料庫 API 重新讀取資料表清單（不然新表、新函式要等快取更新才找得到）
notify pgrst, 'reload schema';
