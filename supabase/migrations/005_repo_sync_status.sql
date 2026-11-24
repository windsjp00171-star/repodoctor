-- 「我的專案」要知道 repo 清單同步好了沒，才能顯示「正在從 GitHub 更新」並自動重新整理。
-- worker 每次同步完寫 repos_synced_at；網站比對 sync_requested_at > repos_synced_at 就代表還在等。
-- 使用者只能讀，不能寫（沿用 001 的欄位權限：authenticated 只有 select）。
alter table public.installations add column if not exists repos_synced_at timestamptz;
