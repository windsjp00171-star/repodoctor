"use client";
import { useState } from "react";
import { copy } from "@/lib/copy";

/** 刪除我的所有資料。確認步驟做在頁面上（不用 confirm()，有些瀏覽器會擋）。 */
export function DeleteMyData() {
  const d = copy.dashboard;
  const [asking, setAsking] = useState(false);
  return (
    <section className="flex flex-col gap-3 rounded-card border border-border p-5">
      <h2 className="font-bold">{d.deleteTitle}</h2>
      <p className="text-sm text-muted">{d.deleteBody}</p>
      {!asking ? (
        <div>
          <button type="button" onClick={() => setAsking(true)}
            className="rounded-md border border-critical/60 px-4 py-2 text-sm text-critical hover:bg-critical/10">
            {d.deleteTitle}
          </button>
        </div>
      ) : (
        <form action="/account/delete" method="post" className="flex flex-wrap gap-2">
          <button className="rounded-md bg-critical px-4 py-2 text-sm font-semibold text-bg">{d.deleteConfirm}</button>
          <button type="button" onClick={() => setAsking(false)} className="rounded-md border border-border px-4 py-2 text-sm text-muted">
            {d.deleteCancel}
          </button>
        </form>
      )}
    </section>
  );
}
