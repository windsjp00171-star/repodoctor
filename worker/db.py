"""Supabase client：整個 worker 只在這裡建立。其他地方一律 `from db import supabase`。

Phase 0 不寫資料庫，沒設環境變數時 `supabase` 是 None。
"""
import os

supabase = None

_url = os.environ.get("SUPABASE_URL")
_key = os.environ.get("SUPABASE_SECRET_KEY")
if _url and _key:
    from supabase import create_client

    supabase = create_client(_url, _key)
