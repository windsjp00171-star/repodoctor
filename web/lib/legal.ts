// 隱私權政策與使用條款的文字（篇幅長，從 copy.ts 分出來；一樣是「集中放在文案檔」）。
// ★ 這裡寫的每一個承諾都要有程式對應：保存天數 = worker/config.py RETENTION_DAYS，
//   刪除帳號 = supabase/migrations/003 + worker/runner.py process_deletion_requests。改這裡要一起改程式。

export const RETENTION_DAYS = 90;
export const UPDATED = "2026 年 11 月 23 日";
export const CONTACT_URL = process.env.NEXT_PUBLIC_CONTACT_URL || "https://github.com/windsjp00171-star";

type Section = { title: string; body?: string; items?: string[] };

export const privacy: { title: string; lede: string; sections: Section[] } = {
  title: "隱私權政策",
  lede: `本政策依《個人資料保護法》第 8 條，說明 RepoDoctor 蒐集哪些個人資料、為什麼蒐集、保存多久，以及你可以怎麼行使權利。最後更新：${UPDATED}。`,
  sections: [
    {
      title: "一、誰在蒐集你的資料",
      body: "RepoDoctor 是由個人開發者營運、目前仍在測試中的程式健檢服務（以下稱「我們」）。聯絡方式見本頁最下方。",
    },
    {
      title: "二、蒐集的目的",
      items: [
        "提供程式健檢服務：登入、讀取你授權的 GitHub repo、產生並保存健檢報告。",
        "防止濫用：限制每人每天的健檢次數。",
        "改善服務：統計健檢次數與 AI 使用成本（不分析你程式碼的內容）。",
      ],
    },
    {
      title: "三、蒐集哪些資料",
      items: [
        "GitHub 帳號資料：帳號名稱、頭像、email（透過「用 GitHub 登入」取得）。",
        "你授權的 GitHub App 安裝資訊與 repo 名稱。",
        "健檢報告：分數、找到的問題、說明、修復指令，以及問題所在的檔名、行號與該行程式片段（片段中的金鑰只保留前 4 碼）。",
        "我們不保存你的程式碼：健檢時暫時下載，健檢結束立刻刪除。",
      ],
    },
    {
      title: "四、保存期間",
      items: [
        `健檢報告的問題細節（檔名、程式片段、修復指令）保存 ${RETENTION_DAYS} 天，到期自動刪除，只留分數與統計。`,
        "帳號資料、分數與 repo 清單保存到你刪除帳號為止。",
        "你按下「刪除我的所有資料」後，帳號與所有相關資料會在下一次系統執行時刪除（通常幾分鐘內）。",
      ],
    },
    {
      title: "五、資料存放地點與使用的服務",
      body: "為了提供服務，你的資料會經過或存放在以下服務商，可能位於台灣以外：",
      items: [
        "Supabase：資料庫與登入（日本東京）。",
        "Vercel：網站主機。",
        "GitHub：登入、讀取 repo、執行健檢（GitHub Actions）。",
        "Anthropic（Claude API）與 Groq：只有你勾選「AI 分析」時才會使用。「登入與權限」送 Anthropic，「重複程式」「規範落差」送 Groq；只送出挑選過的程式片段，所有疑似金鑰會先遮罩。",
        "我們不會把你的資料賣給或提供給其他第三方，也不使用廣告或追蹤分析工具。",
      ],
    },
    {
      title: "六、Cookie",
      body: "網站只使用維持登入狀態所需的 cookie，以及記住你選擇「白話／進階」模式的瀏覽器設定。不使用廣告或追蹤 cookie。",
    },
    {
      title: "七、你的權利",
      body: "依《個人資料保護法》第 3 條，你可以隨時：",
      items: [
        "查詢或閱覽：登入後在「我的專案」與報告頁可以看到我們保存的全部健檢資料。",
        "請求製給複製本、補充或更正：透過下方聯絡方式提出。",
        "請求停止蒐集、處理、利用或刪除：在「我的專案」頁按「刪除我的所有資料」，或到 GitHub 移除 RepoDoctor App，我們就無法再讀取你的 repo。",
      ],
    },
    {
      title: "八、不提供資料的影響",
      body: "你可以自由選擇是否使用本服務。不登入或不授權 GitHub App，就無法使用健檢功能，但不影響你的任何其他權益。",
    },
    {
      title: "九、資料外洩時",
      body: "如果發生資料外洩，我們會依《個人資料保護法》第 12 條，在查明後以 email 通知受影響的使用者，說明發生了什麼事、影響哪些資料，以及我們採取的處理措施。",
    },
    {
      title: "十、政策更新",
      body: "本政策如有修改，會更新本頁的「最後更新」日期；重大變更會在網站上公告。",
    },
  ],
};

export const terms: { title: string; lede: string; sections: Section[] } = {
  title: "使用條款",
  lede: `使用 RepoDoctor 即表示你同意以下條款。最後更新：${UPDATED}。`,
  sections: [
    {
      title: "一、服務內容",
      body: "RepoDoctor 讀取你授權的 GitHub repo，找出常見的資安與程式品質問題，並提供白話說明與修復指令。我們只讀取，不會修改你的程式或在你的 repo 上做任何動作。",
    },
    {
      title: "二、測試中的服務",
      items: [
        "本服務目前免費、仍在測試中，按「現狀」提供，可能有錯誤、中斷或功能變更。",
        "每人每天的健檢次數有上限，以防止濫用並控制成本。",
      ],
    },
    {
      title: "三、健檢結果僅供參考",
      items: [
        "健檢不保證找出所有問題，也可能出現誤報。沒有被列出的問題，不代表你的程式就是安全的。",
        "修復指令（包含 AI 產生的內容）可能不完全正確。請在套用前先看過，並在測試環境確認後再上線。",
        "發現金鑰外洩時，請務必到該服務的後台作廢並更換金鑰；只修改程式並不能讓已外洩的金鑰失效。",
      ],
    },
    {
      title: "四、你的責任",
      items: [
        "只健檢你擁有或有權限處理的 repo。",
        "不得利用本服務攻擊、干擾或探測任何系統，也不得用自動化方式大量呼叫本服務。",
        "妥善保管你的 GitHub 帳號；建議開啟兩步驟驗證。",
      ],
    },
    {
      title: "五、責任限制",
      body: "在法律允許的範圍內，我們不對因使用或無法使用本服務、或依健檢結果與修復指令所做的修改而產生的任何直接或間接損失負責。",
    },
    {
      title: "六、終止",
      body: "你可以隨時刪除帳號並移除 GitHub App。若你違反本條款，我們可以停止你使用本服務。",
    },
    {
      title: "七、條款修改與準據法",
      body: "我們可能修改本條款，並更新本頁日期；修改後繼續使用即表示同意。本條款以中華民國法律為準據法。",
    },
  ],
};

// AGPL-3.0 第 13 條：架成網站時要讓使用者拿得到原始碼
export const SOURCE_URL = "https://github.com/windsjp00171-star/repodoctor";

export const footer = { privacy: "隱私權政策", terms: "使用條款", security: "隱私與安全", contact: "聯絡我們", source: "原始碼（AGPL-3.0）" };
