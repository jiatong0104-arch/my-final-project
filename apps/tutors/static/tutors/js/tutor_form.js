// 老師檔案表單：學校建議清單、高中職、選「其他」才顯示輸入框、自我介紹字數
const isHighSchool = () => document.querySelector("[data-education-level] input:checked")?.value === "high_school";

// 下拉選單（系所）選「其他」時，才顯示自行輸入的欄位
document.querySelectorAll("[data-other-for]").forEach((box) => {
  const select = document.getElementById(box.dataset.otherFor);
  const sync = () => { box.hidden = select.value !== "__other__"; };
  select.addEventListener("change", () => { sync(); if (!box.hidden) box.querySelector("input").focus(); });
  sync();
});

// 最高學歷選「高中職」：校名直接輸入（建議清單都是大學、專科），不用選系所
const schoolInput = document.getElementById("id_school");
const schoolLabel = document.querySelector("[data-school-label]");
const schoolHelp = document.querySelector("[data-school-help]");
const department = document.querySelector("[data-department]");
const syncEducation = () => {
  const highSchool = isHighSchool();
  department.hidden = highSchool;
  schoolLabel.textContent = highSchool ? "高中職校名" : "學校";
  schoolHelp.hidden = highSchool;
  schoolInput.placeholder = highSchool ? "例如：臺北市立建國高級中學" : "輸入校名或簡稱，例如「台大」「成大」";
  schoolInput.dataset.suggest = highSchool ? "off" : "on";
};
document.querySelectorAll("[data-education-level] input").forEach((radio) => radio.addEventListener("change", syncEducation));
syncEducation();

// ── 學校輸入框：邊打字邊顯示建議 ──
// 「台／臺」都找得到，也能用簡稱（台大、成大…）；上下鍵選擇、Enter 確定、Esc 關閉
(function schoolAutocomplete() {
  const options = JSON.parse(document.getElementById("school-options").textContent);
  const listbox = document.getElementById("school-listbox");
  const normalize = (text) => text.replace(/\s+/g, "").replace(/台/g, "臺").toLowerCase();
  let matches = [];
  let active = -1;

  schoolInput.setAttribute("role", "combobox");
  schoolInput.setAttribute("aria-autocomplete", "list");
  schoolInput.setAttribute("aria-controls", "school-listbox");
  schoolInput.setAttribute("aria-expanded", "false");

  function search(query) {
    const q = normalize(query);
    if (!q) return [];
    const scored = [];
    for (const option of options) {
      const name = normalize(option.name);
      const aliases = option.aliases.map(normalize);
      let score = -1;
      if (aliases.includes(q)) score = 0;                          // 簡稱完全一樣：排最前面
      else if (name.replace(/^國立/, "").startsWith(q)) score = 1;  // 開頭符合
      else if (aliases.some((a) => a.startsWith(q))) score = 2;
      else if (name.includes(q)) score = 3;                         // 中間有出現
      if (score >= 0) scored.push([score, option]);
    }
    return scored.sort((a, b) => a[0] - b[0]).slice(0, 8).map(([, option]) => option);
  }

  function close() {
    listbox.hidden = true;
    schoolInput.setAttribute("aria-expanded", "false");
    schoolInput.removeAttribute("aria-activedescendant");
    active = -1;
  }

  function highlight(index) {
    active = index;
    listbox.querySelectorAll("[role=option]").forEach((item, i) => {
      const on = i === index;
      item.setAttribute("aria-selected", String(on));
      item.classList.toggle("bg-teacher-light", on);
      if (on) { schoolInput.setAttribute("aria-activedescendant", item.id); item.scrollIntoView({ block: "nearest" }); }
    });
  }

  function choose(option) {
    schoolInput.value = option.name;
    close();
  }

  function render() {
    listbox.replaceChildren();
    if (schoolInput.dataset.suggest === "off" || !schoolInput.value.trim()) return close();
    matches = search(schoolInput.value);
    // 已經是完整校名，就不用再跳清單
    if (matches.length === 1 && matches[0].name === schoolInput.value.trim()) return close();

    matches.forEach((option, i) => {
      const item = document.createElement("li");
      item.id = `school-option-${i}`;
      item.setAttribute("role", "option");
      item.className = "flex cursor-pointer items-baseline justify-between gap-3 px-4 py-2.5 hover:bg-teacher-light";
      const name = document.createElement("span");
      name.className = "font-medium";
      name.textContent = option.name;
      const group = document.createElement("span");
      group.className = "shrink-0 text-xs text-soft";
      group.textContent = option.group;
      item.append(name, group);
      // 用 mousedown：比輸入框失去焦點（blur）早發生，清單才不會先關掉
      item.addEventListener("mousedown", (event) => { event.preventDefault(); choose(option); });
      listbox.append(item);
    });
    if (!matches.length) {
      const empty = document.createElement("li");
      empty.className = "px-4 py-2.5 text-sm text-soft";
      empty.textContent = "清單上沒有也沒關係，輸入完整校名就可以了。";
      listbox.append(empty);
    }
    listbox.hidden = false;
    schoolInput.setAttribute("aria-expanded", "true");
    highlight(matches.length ? 0 : -1);
  }

  schoolInput.addEventListener("input", render);
  schoolInput.addEventListener("focus", render);
  schoolInput.addEventListener("blur", close);
  schoolInput.addEventListener("keydown", (event) => {
    if (listbox.hidden || !matches.length) return;
    if (event.key === "ArrowDown") { event.preventDefault(); highlight((active + 1) % matches.length); }
    else if (event.key === "ArrowUp") { event.preventDefault(); highlight((active - 1 + matches.length) % matches.length); }
    else if (event.key === "Enter" && !event.isComposing && active >= 0) { event.preventDefault(); choose(matches[active]); }
    else if (event.key === "Escape") { close(); }
  });
})();

// 科目勾選「其他」時，才顯示輸入框；取消勾選會清空
document.querySelectorAll("[data-other-toggle]").forEach((checkbox) => {
  const box = document.querySelector(`[data-other-box="${checkbox.dataset.otherToggle}"]`);
  const input = box.querySelector("input");
  const sync = () => { box.hidden = !checkbox.checked; };
  checkbox.addEventListener("change", () => {
    sync();
    if (checkbox.checked) input.focus(); else input.value = "";
  });
  sync();
});

// 自我介紹字數
const bio = document.getElementById("id_bio");
const count = document.getElementById("bio-count");
const updateCount = () => { count.textContent = `${bio.value.length} / 5000 字`; };
bio.addEventListener("input", updateCount);
updateCount();
