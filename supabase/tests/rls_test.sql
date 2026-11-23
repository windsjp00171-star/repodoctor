-- RLS 與欄位權限的測試。跑法見 supabase/tests/run.sh。
-- 每一段都是「使用者想做一件不該做的事 → 必須失敗」或「該做的事 → 必須成功」。
\set ON_ERROR_STOP on
set client_min_messages = warning;

-- 兩個使用者（identity 先建，trigger 才讀得到 github_login）
insert into auth.users (id) values ('00000000-0000-0000-0000-00000000000a'), ('00000000-0000-0000-0000-00000000000b');

-- service role（worker）建資料
set role service_role;
insert into public.installations (id, user_id, github_installation_id, status)
  values ('10000000-0000-0000-0000-00000000000a', '00000000-0000-0000-0000-00000000000a', 111, 'active'),
         ('10000000-0000-0000-0000-00000000000b', '00000000-0000-0000-0000-00000000000b', 222, 'active');
insert into public.repos (id, user_id, installation_id, github_repo_id, full_name)
  values ('20000000-0000-0000-0000-00000000000a', '00000000-0000-0000-0000-00000000000a', '10000000-0000-0000-0000-00000000000a', 1, 'a/app'),
         ('20000000-0000-0000-0000-00000000000b', '00000000-0000-0000-0000-00000000000b', '10000000-0000-0000-0000-00000000000b', 2, 'b/app');
reset role;

create function pg_temp.expect_fail(sql text, why text) returns void language plpgsql as $$
begin
  execute sql;
  raise exception 'SHOULD HAVE FAILED: %', why;
exception when others then
  if sqlerrm like 'SHOULD HAVE FAILED%' then raise; end if;
end $$;

-- 以使用者 A 的身分
set role authenticated;
select set_config('request.jwt.claim.sub', '00000000-0000-0000-0000-00000000000a', false);

-- ✔ 只看得到自己的 repo
do $$ begin
  if (select count(*) from public.repos) <> 1 then raise exception 'A should see exactly 1 repo'; end if;
end $$;

-- ✔ 可以對自己的 repo 發起健檢，status 一律 queued
insert into public.scans (repo_id, use_ai) values ('20000000-0000-0000-0000-00000000000a', false);
do $$ begin
  if (select status from public.scans) <> 'queued' then raise exception 'new scan must be queued'; end if;
end $$;

-- ✘ 不能對別人的 repo 發起健檢
select pg_temp.expect_fail($$insert into public.scans (repo_id) values ('20000000-0000-0000-0000-00000000000b')$$, 'scan on B''s repo');
-- ✘ 不能自己把健檢標成完成、填分數
select pg_temp.expect_fail($$insert into public.scans (repo_id, status, score) values ('20000000-0000-0000-0000-00000000000a', 'done', 100)$$, 'set status/score');
select pg_temp.expect_fail($$update public.scans set score = 100$$, 'update score');
-- ✘ 不能替別人新增安裝
select pg_temp.expect_fail($$insert into public.installations (user_id, github_installation_id) values ('00000000-0000-0000-0000-00000000000b', 999)$$, 'installation for B');
-- ✘ 不能自己把安裝標成 active
select pg_temp.expect_fail($$insert into public.installations (github_installation_id, status) values (999, 'active')$$, 'self-activate installation');
-- ✔ 可以新增自己的安裝（pending，等 worker 驗證）
insert into public.installations (github_installation_id) values (333);
do $$ begin
  if (select status from public.installations where github_installation_id = 333) <> 'pending' then raise exception 'must be pending'; end if;
end $$;
-- ✘ 不能自己新增 repo、寫 findings、改方案
select pg_temp.expect_fail($$insert into public.repos (user_id, installation_id, github_repo_id, full_name) values ('00000000-0000-0000-0000-00000000000a', '10000000-0000-0000-0000-00000000000b', 9, 'b/secret')$$, 'insert repo');
select pg_temp.expect_fail($$insert into public.findings (scan_id, user_id, category, severity, title, plain_explanation, advanced_explanation, fix_prompt, fingerprint) select id, user_id, 'x','low','t','p','a','f','fp' from public.scans limit 1$$, 'insert finding');
select pg_temp.expect_fail($$update public.profiles set plan = 'pro'$$, 'upgrade own plan');
-- ✘ 不能呼叫 worker 專用的 claim
select pg_temp.expect_fail($$select * from public.claim_next_scan()$$, 'claim_next_scan');

-- 以使用者 B 的身分：看不到 A 的健檢
select set_config('request.jwt.claim.sub', '00000000-0000-0000-0000-00000000000b', false);
do $$ begin
  if (select count(*) from public.scans) <> 0 then raise exception 'B must not see A''s scans'; end if;
end $$;

-- anon 什麼都看不到
set role anon;
select pg_temp.expect_fail($$select * from public.scans$$, 'anon read scans');

-- worker 搶任務：同一個只會被搶一次
reset role;
set role service_role;
do $$ begin
  if (select count(*) from public.claim_next_scan()) <> 1 then raise exception 'claim should return the queued scan'; end if;
  if (select count(*) from public.claim_next_scan()) <> 0 then raise exception 'second claim should be empty'; end if;
end $$;
reset role;

-- ── 002：叫醒 worker ──
-- 沒放 token：照樣能發起健檢，不送任何請求
set role authenticated;
select set_config('request.jwt.claim.sub', '00000000-0000-0000-0000-00000000000a', false);
insert into public.scans (repo_id) values ('20000000-0000-0000-0000-00000000000a');
reset role;
do $$ begin
  if (select count(*) from net.calls) <> 0 then raise exception 'no token: must not call GitHub'; end if;
end $$;
-- 放了 token：發起健檢、新增安裝都會叫一次，而且 token 只出現在 header
insert into vault.decrypted_secrets values ('github_dispatch_token', 'tok_test');
set role authenticated;
insert into public.scans (repo_id) values ('20000000-0000-0000-0000-00000000000a');
insert into public.installations (github_installation_id) values (444);
reset role;
do $$ begin
  if (select count(*) from net.calls) <> 2 then raise exception 'expected 2 dispatch calls, got %', (select count(*) from net.calls); end if;
  if exists (select 1 from net.calls where url not like '%/actions/workflows/worker.yml/dispatches') then raise exception 'wrong url'; end if;
  if exists (select 1 from net.calls where body::text like '%tok_test%') then raise exception 'token leaked into body'; end if;
end $$;
-- 使用者不能自己呼叫叫醒函式
set role authenticated;
select pg_temp.expect_fail($$select public.kick_worker()$$, 'call kick_worker directly');
reset role;

-- ── 刪除我的所有資料：只刪自己的，健檢與結果一起刪，別人的不受影響 ──
set role service_role;
insert into public.findings (scan_id, user_id, category, severity, title, plain_explanation, advanced_explanation, fix_prompt, fingerprint)
  select id, user_id, 'secrets', 'critical', 't', 'p', 'a', 'f', 'fp' from public.scans
  where user_id = '00000000-0000-0000-0000-00000000000a' limit 1;
insert into public.scans (repo_id, user_id) values ('20000000-0000-0000-0000-00000000000b', '00000000-0000-0000-0000-00000000000b');
reset role;
set role authenticated;
select set_config('request.jwt.claim.sub', '00000000-0000-0000-0000-00000000000a', false);
delete from public.installations where user_id = '00000000-0000-0000-0000-00000000000a';
reset role;
do $$ begin
  if exists (select 1 from public.installations where user_id = '00000000-0000-0000-0000-00000000000a') then raise exception 'A installations left'; end if;
  if exists (select 1 from public.repos where user_id = '00000000-0000-0000-0000-00000000000a') then raise exception 'A repos left'; end if;
  if exists (select 1 from public.scans where user_id = '00000000-0000-0000-0000-00000000000a') then raise exception 'A scans left'; end if;
  if exists (select 1 from public.findings where user_id = '00000000-0000-0000-0000-00000000000a') then raise exception 'A findings left'; end if;
  if not exists (select 1 from public.scans where user_id = '00000000-0000-0000-0000-00000000000b') then raise exception 'B data must survive'; end if;
end $$;
-- B 不能刪 A 的（RLS 擋下：刪 0 筆，不報錯）
set role authenticated;
select set_config('request.jwt.claim.sub', '00000000-0000-0000-0000-00000000000a', false);
delete from public.installations where user_id = '00000000-0000-0000-0000-00000000000b';
reset role;
do $$ begin
  if not exists (select 1 from public.installations where user_id = '00000000-0000-0000-0000-00000000000b') then raise exception 'A deleted B''s data'; end if;
end $$;

select 'ALL RLS TESTS PASSED';
