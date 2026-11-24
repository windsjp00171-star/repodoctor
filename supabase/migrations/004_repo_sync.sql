-- 使用者到 GitHub「新增或調整可以健檢的 repo」之後，清單要跟著更新。
--
-- 原本只有「第一次安裝」會同步 repo 清單：之後再加 repo，安裝已經存在（同一個 id 撞 unique），
-- 什麼都不會發生，新加的 repo 永遠不會出現在「我的專案」。
--
-- 現在：網站在使用者從 GitHub 回來時填 sync_requested_at → 叫醒 worker；
-- worker 每次執行都會重新拉一次所有 active 安裝的 repo 清單（排程那一次也會補上）。

alter table public.installations add column if not exists sync_requested_at timestamptz;
grant update (sync_requested_at) on public.installations to authenticated;
create policy "request repo sync" on public.installations for update to authenticated
  using (user_id = (select auth.uid())) with check (user_id = (select auth.uid()));

create trigger kick_worker_on_sync_request
  after update of sync_requested_at on public.installations
  for each row when (new.sync_requested_at is distinct from old.sync_requested_at)
  execute function public.kick_worker();
