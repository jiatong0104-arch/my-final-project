// 手機版導覽列：點漢堡按鈕展開／收合選單
const toggle = document.getElementById("nav-toggle");
const menu = document.getElementById("nav-menu");
toggle.addEventListener("click", () => {
  const open = menu.classList.toggle("hidden") === false;
  menu.classList.toggle("flex", open);
  toggle.setAttribute("aria-expanded", String(open));
});

// 提示訊息的關閉按鈕
document.querySelectorAll("[data-dismiss]").forEach((button) => {
  button.addEventListener("click", () => button.parentElement.remove());
});

// 下拉選單一改變就送出表單（例如老師列表的「排序」）
document.querySelectorAll("[data-autosubmit]").forEach((select) => {
  select.addEventListener("change", () => select.form.submit());
});
