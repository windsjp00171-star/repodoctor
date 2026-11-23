#!/usr/bin/env bash
# 在一般 Postgres 上跑 migration ＋ RLS 測試。用法：PGHOST=/tmp PGPORT=55432 PGUSER=postgres bash supabase/tests/run.sh
set -euo pipefail
cd "$(dirname "$0")/.."
DB=rd_rls_test
psql -qX -d postgres -c "drop database if exists $DB" -c "create database $DB"
psql -qX -v ON_ERROR_STOP=1 -d $DB -f tests/supabase_stub.sql
psql -qX -v ON_ERROR_STOP=1 -d $DB -f migrations/001_init.sql
psql -qX -v ON_ERROR_STOP=1 -d $DB -f migrations/002_kick_worker.sql
psql -qX -v ON_ERROR_STOP=1 -d $DB -tA -f tests/rls_test.sql
