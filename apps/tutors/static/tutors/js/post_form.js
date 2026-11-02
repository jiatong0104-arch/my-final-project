// 老師發動態：選了照片或影片就顯示預覽；照片、影片只能二選一；送出時顯示「上傳中」
const postForm = document.getElementById("post-form");
const inputs = postForm.querySelectorAll("input[type=file]");
const preview = document.getElementById("post-preview");
const previewImage = document.getElementById("preview-image");
const previewVideo = document.getElementById("preview-video");
const previewName = document.getElementById("preview-name");
const fileError = document.getElementById("post-file-error");
const limits = { image: Number(postForm.dataset.imageLimit), video: Number(postForm.dataset.videoLimit) };
let objectUrl = null;

function clearPreview() {
  if (objectUrl) URL.revokeObjectURL(objectUrl);
  objectUrl = null;
  preview.classList.add("hidden");
  previewImage.classList.add("hidden");
  previewVideo.classList.add("hidden");
  previewImage.removeAttribute("src");
  previewVideo.removeAttribute("src");
}

inputs.forEach((input) => {
  input.addEventListener("change", () => {
    fileError.classList.add("hidden");
    const file = input.files[0];
    if (!file) return;

    const kind = input.dataset.kind;
    if (file.size > limits[kind] * 1024 * 1024) {
      fileError.textContent = `檔案太大了（${(file.size / 1024 / 1024).toFixed(0)} MB），上限是 ${limits[kind]} MB。`;
      fileError.classList.remove("hidden");
      input.value = "";
      return;
    }
    // 照片和影片只能選一個：選了其中一個，就清掉另一個
    inputs.forEach((other) => { if (other !== input) other.value = ""; });

    clearPreview();
    objectUrl = URL.createObjectURL(file);
    const target = kind === "image" ? previewImage : previewVideo;
    target.src = objectUrl;
    target.classList.remove("hidden");
    previewName.textContent = file.name;
    preview.classList.remove("hidden");
  });
});

document.getElementById("preview-remove").addEventListener("click", () => {
  inputs.forEach((input) => { input.value = ""; });
  clearPreview();
});

postForm.addEventListener("submit", () => {
  const button = postForm.querySelector("button[type=submit]");
  button.disabled = true;
  button.textContent = [...inputs].some((input) => input.files.length) ? "上傳中，請稍候…" : "發布中…";
});
