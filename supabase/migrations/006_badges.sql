-- 健檢徽章：使用者「自己選擇」公開某個 repo 的健檢結果，貼在 README 或作品網站上。
--
-- 對外只給三樣東西：分數、有沒有緊急問題、健檢時間。不給 repo 名稱、不給任何問題內容——
-- 公開「這個網站有哪些漏洞」等於告訴壞人去攻擊哪一個。
-- 徽章 id 是隨機 UUID；刪掉徽章（或刪帳號）就立刻失效。徽章永遠顯示這個 repo「最新一次」的結果。

create table public.badges (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null default auth.uid() references auth.users (id) on delete cascade,
  repo_id     uuid not null references public.repos (id) on delete cascade,
  created_at  timestamptz not null default now(),
  unique (repo_id)
);

alter table public.badges enable row level security;
create policy "own badges"    on public.badges for select to authenticated using (user_id = (select auth.uid()));
create policy "add badge"     on public.badges for insert to authenticated
  with check (user_id = (select auth.uid())
              and exists (select 1 from public.repos r where r.id = repo_id and r.user_id = (select auth.uid())));
create policy "remove badge"  on public.badges for delete to authenticated using (user_id = (select auth.uid()));

revoke all on public.badges from anon, authenticated;
grant select, delete on public.badges to authenticated;
grant insert (repo_id) on public.badges to authenticated;
grant all on public.badges to service_role;

-- 唯一對外（沒登入也能呼叫）的讀取口：只回傳分數、有沒有緊急問題、時間
create function public.badge_status(badge_id uuid)
returns table (score int, has_critical boolean, finished_at timestamptz)
language sql stable security definer set search_path = '' as $$
  select s.score, coalesce((s.summary ->> 'critical')::int, 0) > 0, s.finished_at
  from public.badges b
  join public.scans s on s.repo_id = b.repo_id and s.status = 'done'
  where b.id = badge_id
  order by s.finished_at desc nulls last
  limit 1;
$$;
revoke all on function public.badge_status(uuid) from public;
grant execute on function public.badge_status(uuid) to anon, authenticated;

-- 通知 Supabase 的資料庫 API 重新讀取資料表清單（不然新表、新函式要等快取更新才找得到）
notify pgrst, 'reload schema';
