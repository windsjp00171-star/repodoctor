-- 免費版健檢主機（GitHub Actions）的叫醒鈴：
-- 有人發起健檢、或新增 GitHub App 安裝時，立刻呼叫 GitHub API 觸發 worker workflow。
-- 沒有這個的話，只能等每 3 小時的排程，測試者會以為壞了。
--
-- 需要先在 Vault 放一把 GitHub token（只有 repodoctor repo 的 Actions: Read and write）：
--   select vault.create_secret('<token>', 'github_dispatch_token');
-- 沒放 token 時什麼都不做（不會讓健檢發起失敗），排程照樣會處理。
-- 改用 Render 常駐之後，這個 trigger 可以留著（多叫一次無害）或刪掉。

do $$ begin
  if not exists (select 1 from pg_namespace where nspname = 'net') then
    create extension pg_net;
  end if;
end $$;

create function public.kick_worker() returns trigger
language plpgsql security definer set search_path = '' as $$
declare
  tok text;
begin
  select decrypted_secret into tok from vault.decrypted_secrets where name = 'github_dispatch_token' limit 1;
  if tok is null then
    return new;
  end if;
  -- 非同步送出：GitHub 回什麼都不會擋住這筆寫入
  perform net.http_post(
    url     := 'https://api.github.com/repos/windsjp00171-star/repodoctor/actions/workflows/worker.yml/dispatches',
    body    := '{"ref": "main"}'::jsonb,
    headers := jsonb_build_object(
      'Authorization', 'Bearer ' || tok,
      'Accept', 'application/vnd.github+json',
      'X-GitHub-Api-Version', '2022-11-28',
      'User-Agent', 'repodoctor',
      'Content-Type', 'application/json'
    )
  );
  return new;
end $$;
revoke all on function public.kick_worker() from public, anon, authenticated;

create trigger kick_worker_on_scan after insert on public.scans
  for each row execute function public.kick_worker();
create trigger kick_worker_on_installation after insert on public.installations
  for each row execute function public.kick_worker();

-- 通知 Supabase 的資料庫 API 重新讀取資料表清單（不然新表、新函式要等快取更新才找得到）
notify pgrst, 'reload schema';
