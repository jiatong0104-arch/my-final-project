// 聊天室：送出訊息（POST）、每 3 秒查詢新訊息（GET + JsonResponse）、標記已讀（POST）
const log = document.getElementById("chat-log");
const form = document.getElementById("chat-form");
const input = document.getElementById("id_body");
const button = form.querySelector("button");
const errorBox = document.getElementById("chat-error");
const csrf = form.querySelector("[name=csrfmiddlewaretoken]").value;
// 網址由模板放在 data- 屬性上，JS 檔案裡不寫死網址
const pollUrl = log.dataset.pollUrl;
const readUrl = log.dataset.readUrl;

// 標記已讀會改變資料，所以用 POST（GET 只負責讀取）
async function markRead() {
  try {
    await fetch(readUrl, { method: "POST", headers: { Accept: "application/json", "X-CSRFToken": csrf } });
  } catch (e) { /* 下一次收到新訊息時會再標記 */ }
}

const lastId = () => {
  const items = log.querySelectorAll("[data-id]");
  return items.length ? Number(items[items.length - 1].dataset.id) : 0;
};
const lastDate = () => {
  const dates = log.querySelectorAll("[data-date]");
  return dates.length ? dates[dates.length - 1].dataset.date : null;
};
const scrollToBottom = () => { log.scrollTop = log.scrollHeight; };
const nearBottom = () => log.scrollHeight - log.scrollTop - log.clientHeight < 120;

function addMessage(m) {
  if (log.querySelector(`[data-id="${m.id}"]`)) return;
  document.getElementById("chat-empty")?.remove();

  if (m.date !== lastDate()) {
    const [, month, day] = m.date.split("-").map(Number);
    const sep = document.createElement("p");
    sep.className = "py-2 text-center text-xs text-soft";
    sep.dataset.date = m.date;
    sep.textContent = `${month} 月 ${day} 日`;
    log.append(sep);
  }

  const row = document.createElement("div");
  row.className = "flex" + (m.mine ? " justify-end" : "");
  row.dataset.id = m.id;
  const wrap = document.createElement("div");
  wrap.className = "max-w-[80%]";
  const bubble = document.createElement("p");
  bubble.className = "whitespace-pre-wrap break-words rounded-2xl px-4 py-2.5 leading-6 " +
    (m.mine ? "rounded-br-md bg-ink text-white" : "rounded-bl-md border border-grid bg-white");
  bubble.textContent = m.body;  // 用 textContent，避免訊息內容被當成 HTML 執行
  const time = document.createElement("p");
  time.className = "mt-1 text-xs text-soft" + (m.mine ? " text-right" : "");
  time.textContent = m.time;
  wrap.append(bubble, time);
  row.append(wrap);
  log.append(row);
}

async function poll() {
  try {
    const response = await fetch(`${pollUrl}?after=${lastId()}`, { headers: { Accept: "application/json" } });
    if (!response.ok) return;
    const data = await response.json();
    if (data.messages.length) {
      const stick = nearBottom();
      data.messages.forEach(addMessage);
      if (stick) scrollToBottom();
      if (data.messages.some((m) => !m.mine)) markRead();
    }
  } catch (e) { /* 網路暫時中斷時，下一輪再試 */ }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const body = input.value.trim();
  if (!body) return;
  button.disabled = true;
  errorBox.classList.add("hidden");
  try {
    const response = await fetch(form.action || location.href, {
      method: "POST",
      headers: { Accept: "application/json", "X-CSRFToken": csrf },
      body: new URLSearchParams({ body }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "訊息沒有送出，請再試一次。");
    addMessage(data.message);
    input.value = "";
    input.style.height = "";
    scrollToBottom();
  } catch (error) {
    errorBox.textContent = error.message || "訊息沒有送出，請檢查網路後再試一次。";
    errorBox.classList.remove("hidden");
  } finally {
    button.disabled = false;
    input.focus();
  }
});

// Enter 送出、Shift + Enter 換行（中文輸入法選字時不送出）
input.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
    event.preventDefault();
    form.requestSubmit();
  }
});
// 輸入框隨內容長高
input.addEventListener("input", () => {
  input.style.height = "auto";
  input.style.height = Math.min(input.scrollHeight, 160) + "px";
});

scrollToBottom();
markRead();
setInterval(poll, 3000);
