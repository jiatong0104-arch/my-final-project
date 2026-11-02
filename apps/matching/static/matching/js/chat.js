// 聊天室：送出訊息與圖片（POST）、每 3 秒查詢新訊息（GET + JsonResponse）、標記已讀（POST）
const log = document.getElementById("chat-log");
const form = document.getElementById("chat-form");
const input = document.getElementById("id_body");
const imageInput = document.getElementById("id_image");
const preview = document.getElementById("chat-preview");
const previewImage = document.getElementById("chat-preview-image");
const imageLimit = Number(form.dataset.imageLimit);
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
const nearBottom = (gap = 120) => log.scrollHeight - log.scrollTop - log.clientHeight < gap;

// ── 選擇圖片：顯示預覽，按送出才上傳 ──
let previewUrl = null;
function clearImage() {
  imageInput.value = "";
  if (previewUrl) URL.revokeObjectURL(previewUrl);
  previewUrl = null;
  preview.classList.add("hidden");
  preview.classList.remove("flex");
}
function showError(text) {
  errorBox.textContent = text;
  errorBox.classList.remove("hidden");
}
function useImage(file) {
  errorBox.classList.add("hidden");
  if (!file.type.startsWith("image/")) { clearImage(); return showError("只能傳送圖片。"); }
  if (file.size > imageLimit * 1024 * 1024) { clearImage(); return showError(`圖片太大了，上限是 ${imageLimit} MB。`); }
  if (previewUrl) URL.revokeObjectURL(previewUrl);
  previewUrl = URL.createObjectURL(file);
  previewImage.src = previewUrl;
  preview.classList.remove("hidden");
  preview.classList.add("flex");
  input.focus();
}
imageInput.addEventListener("change", () => { if (imageInput.files[0]) useImage(imageInput.files[0]); });
document.getElementById("chat-preview-remove").addEventListener("click", clearImage);
// 直接貼上截圖（Ctrl + V）也可以
input.addEventListener("paste", (event) => {
  const file = [...event.clipboardData.files].find((f) => f.type.startsWith("image/"));
  if (!file) return;
  event.preventDefault();
  const transfer = new DataTransfer();
  transfer.items.add(file);
  imageInput.files = transfer.files;
  useImage(file);
});

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
  if (m.image_url) {
    // 圖片網址會經過 ChatImageView 檢查是不是聊天的兩人
    const link = document.createElement("a");
    link.href = m.image_url;
    link.target = "_blank";
    link.rel = "noopener";
    link.className = "block w-fit" + (m.mine ? " ml-auto" : "");
    const img = document.createElement("img");
    img.src = m.image_url;
    img.alt = m.mine ? "你傳的圖片" : "對方傳的圖片";
    img.className = "max-h-72 max-w-full rounded-2xl border border-grid bg-white object-contain";
    img.addEventListener("load", () => { if (nearBottom(300)) scrollToBottom(); });
    link.append(img);
    wrap.append(link);
  }
  if (m.body) {
    const bubble = document.createElement("p");
    bubble.className = (m.image_url ? "mt-1 " : "") + "whitespace-pre-wrap break-words rounded-2xl px-4 py-2.5 leading-6 " +
      (m.mine ? "rounded-br-md bg-ink text-white" : "rounded-bl-md border border-grid bg-white");
    bubble.textContent = m.body;  // 用 textContent，避免訊息內容被當成 HTML 執行
    wrap.append(bubble);
  }
  const time = document.createElement("p");
  time.className = "mt-1 text-xs text-soft" + (m.mine ? " text-right" : "");
  time.textContent = m.time;
  wrap.append(time);
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
  const image = imageInput.files[0];
  if (!body && !image) return;
  button.disabled = true;
  button.textContent = image ? "傳送中…" : "送出";
  errorBox.classList.add("hidden");
  // FormData 可以同時放文字和檔案（multipart/form-data）
  const data = new FormData();
  data.append("body", body);
  if (image) data.append("image", image);
  try {
    const response = await fetch(form.action || location.href, {
      method: "POST",
      headers: { Accept: "application/json", "X-CSRFToken": csrf },
      body: data,
    });
    const result = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(result.error || "訊息沒有送出，請再試一次。");
    addMessage(result.message);
    clearImage();
    input.value = "";
    input.style.height = "";
    scrollToBottom();
  } catch (error) {
    showError(error.message || "訊息沒有送出，請檢查網路後再試一次。");
  } finally {
    button.disabled = false;
    button.textContent = "送出";
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
