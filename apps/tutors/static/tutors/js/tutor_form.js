// 老師檔案表單：選「其他」才顯示輸入框、自我介紹字數
const isHighSchool = () => document.querySelector("[data-education-level] input:checked")?.value === "high_school";

// 下拉選單選「其他」時，才顯示自行輸入的欄位
document.querySelectorAll("[data-other-for]").forEach((box) => {
  const select = document.getElementById(box.dataset.otherFor);
  const isSchool = box.dataset.otherFor === "id_school_choice";
  const sync = () => {
    // 高中職：學校清單都是大學，所以直接顯示輸入框
    box.hidden = !(select.value === "__other__" || (isSchool && isHighSchool()));
  };
  select.addEventListener("change", () => { sync(); if (!box.hidden) box.querySelector("input").focus(); });
  document.querySelectorAll("[data-education-level] input").forEach((radio) => radio.addEventListener("change", sync));
  sync();
});

// 最高學歷選「高中職」：只填學校名稱，不用選系所
const schoolSelect = document.querySelector("[data-school-select]");
const department = document.querySelector("[data-department]");
const schoolOtherLabel = document.querySelector("label[for=id_school_other]");
const syncEducation = () => {
  const highSchool = isHighSchool();
  schoolSelect.hidden = highSchool;
  department.hidden = highSchool;
  if (schoolOtherLabel) schoolOtherLabel.firstChild.textContent = highSchool ? "高中職校名" : "學校名稱";
};
document.querySelectorAll("[data-education-level] input").forEach((radio) => radio.addEventListener("change", syncEducation));
syncEducation();

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
