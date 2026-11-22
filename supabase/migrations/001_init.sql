-- RepoDoctor Phase 1：SPEC「資料模型」五張表。
-- 原則：每張表都開 RLS（自己的產品不能犯自己檢查的錯）。
--   使用者（authenticated）只看得到自己的資料，只能寫「發起」類的欄位；
--   驗證 GitHub 安裝、寫入健檢結果，一律由 worker 用 service role 做。
--   這樣就算有人繞過網站、直接打 API，也偽造不出「指向別人 repo」的資料。

-- ── profiles ──────────────────────────────────────────────
create table public.profiles (
  id            uuid primary key references auth.users (id) on delete cascade,
  github_login  text,
  plan          text not null default 'free' check (plan in ('free', 'pro', 'student')),
  report_mode   text not null default 'plain' check (report_mode in ('plain', 'advanced')),
  created_at    timestamptz not null default now()
);

-- 新使用者登入時自動建 profile。github_login 取自 identities（使用者改不到），不是 user_metadata。
create function public.handle_new_user() returns trigger
language plpgsql security definer set search_path = '' as $$
begin
  insert into public.profiles (id, github_login)
  values (
    new.id,
    (select i.identity_data ->> 'user_name' from auth.identities i
      where i.user_id = new.id and i.provider = 'github' limit 1)
  )
  on conflict (id) do nothing;
  return new;
end $$;
create trigger on_auth_user_created after insert on auth.users
  for each row execute function public.handle_new_user();

-- ── installations ─────────────────────────────────────────
-- 網站只寫 github_installation_id（狀態一律 pending），worker 驗證「這個安裝真的是這個人的」才改成 active。
create table public.installations (
  id                      uuid primary key default gen_random_uuid(),
  user_id                 uuid not null default auth.uid() references auth.users (id) on delete cascade,
  github_installation_id  bigint not null,
  account_login           text,
  status                  text not null default 'pending' check (status in ('pending', 'active', 'rejected')),
  note                    text,
  created_at              timestamptz not null default now(),
  unique (user_id, github_installation_id)
);

-- ── repos ─────────────────────────────────────────────────
-- 只有 worker 寫入（驗證過安裝之後，從 GitHub 拉清單）。
create table public.repos (
  id               uuid primary key default gen_random_uuid(),
  user_id          uuid not null references auth.users (id) on delete cascade,
  installation_id  uuid not null references public.installations (id) on delete cascade,
  github_repo_id   bigint not null,
  full_name        text not null,
  default_branch   text,
  language         text,
  last_scan_id     uuid,
  created_at       timestamptz not null default now(),
  unique (installation_id, github_repo_id)
);

-- ── scans ─────────────────────────────────────────────────
-- 使用者只能新增（repo_id、use_ai），其他欄位都由 worker 寫。progress / current_file 給 Realtime 訂閱。
create table public.scans (
  id               uuid primary key default gen_random_uuid(),
  repo_id          uuid not null references public.repos (id) on delete cascade,
  user_id          uuid not null default auth.uid() references auth.users (id) on delete cascade,
  use_ai           boolean not null default false,
  status           text not null default 'queued' check (status in ('queued', 'running', 'done', 'failed')),
  progress         int not null default 0 check (progress between 0 and 100),
  stage            text,
  current_file     text,
  found            int not null default 0,
  score            int,
  category_scores  jsonb,
  summary          jsonb,
  coverage         jsonb,
  meta             jsonb,     -- project、files_scanned、languages
  map              jsonb,     -- 白話地圖（Phase 2）
  commit_sha       text,
  token_usage      jsonb,
  error            text,
  created_at       timestamptz not null default now(),
  started_at       timestamptz,
  finished_at      timestamptz
);
create index scans_queue_idx on public.scans (created_at) where status = 'queued';
create index scans_user_idx on public.scans (user_id, created_at desc);

alter table public.repos
  add constraint repos_last_scan_fk foreign key (last_scan_id) references public.scans (id) on delete set null;

-- ── findings ──────────────────────────────────────────────
create table public.findings (
  id                    uuid primary key default gen_random_uuid(),
  scan_id               uuid not null references public.scans (id) on delete cascade,
  user_id               uuid not null references auth.users (id) on delete cascade,
  category              text not null,
  severity              text not null check (severity in ('critical', 'high', 'medium', 'low')),
  title                 text not null,
  plain_explanation     text not null,
  advanced_explanation  text not null,
  file_path             text,
  line                  int,
  masked_snippet        text,          -- 金鑰只留前 4 碼
  fix_prompt            text not null,
  fingerprint           text not null, -- 比較前後兩次健檢「修好了哪些」
  source                text not null default 'rule',
  confidence            text,
  created_at            timestamptz not null default now()
);
create index findings_scan_idx on public.findings (scan_id);

-- ── RLS ──────────────────────────────────────────────────
alter table public.profiles      enable row level security;
alter table public.installations enable row level security;
alter table public.repos         enable row level security;
alter table public.scans         enable row level security;
alter table public.findings      enable row level security;

create policy "own profile"        on public.profiles      for select to authenticated using (id = (select auth.uid()));
create policy "update own profile" on public.profiles      for update to authenticated using (id = (select auth.uid())) with check (id = (select auth.uid()));
create policy "own installations"  on public.installations for select to authenticated using (user_id = (select auth.uid()));
create policy "add installation"   on public.installations for insert to authenticated with check (user_id = (select auth.uid()));
create policy "remove installation" on public.installations for delete to authenticated using (user_id = (select auth.uid()));
create policy "own repos"          on public.repos         for select to authenticated using (user_id = (select auth.uid()));
create policy "own scans"          on public.scans         for select to authenticated using (user_id = (select auth.uid()));
create policy "start scan on own repo" on public.scans     for insert to authenticated
  with check (
    user_id = (select auth.uid())
    and exists (select 1 from public.repos r where r.id = repo_id and r.user_id = (select auth.uid()))
  );
create policy "own findings"       on public.findings      for select to authenticated using (user_id = (select auth.uid()));

-- 欄位層級：使用者能改、能新增的欄位只有這些（plan、status、分數等只有 worker 能寫）
revoke insert, update, delete on public.profiles, public.installations, public.repos, public.scans, public.findings from anon, authenticated;
grant update (report_mode) on public.profiles to authenticated;
grant insert (github_installation_id) on public.installations to authenticated;
grant delete on public.installations to authenticated;
grant insert (repo_id, use_ai) on public.scans to authenticated;
revoke all on public.profiles, public.installations, public.repos, public.scans, public.findings from anon;

-- ── worker 用：搶下一個待辦的健檢（多個 worker 同時跑也不會搶到同一個）──
create function public.claim_next_scan() returns setof public.scans
language sql security definer set search_path = '' as $$
  update public.scans s set status = 'running', started_at = now(), stage = '準備中'
  where s.id = (
    select id from public.scans where status = 'queued'
    order by created_at for update skip locked limit 1
  )
  returning s.*;
$$;
revoke all on function public.claim_next_scan() from public, anon, authenticated;
grant execute on function public.claim_next_scan() to service_role;
revoke all on function public.handle_new_user() from public, anon, authenticated;

-- ── Realtime：網站訂閱掃描進度 ──
alter publication supabase_realtime add table public.scans;
