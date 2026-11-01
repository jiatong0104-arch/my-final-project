// 老師檔案表單：選「其他」才顯示輸入框、自我介紹字數
// 下拉選單選「其他」時，才顯示自行輸入的欄位
document.querySelectorAll("[data-other-for]").forEach((box) => {
  const select = document.getElementById(box.dataset.otherFor);
  const sync = () => { box.hidden = select.value !== "__other__"; };
  select.addEventListener("change", () => { sync(); if (!box.hidden) box.querySelector("input").focus(); });
  sync();
});

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
