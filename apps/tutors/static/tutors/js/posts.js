// 老師主頁的動態櫥窗：左右箭頭一次捲一張卡片；文字太長時顯示「看全文」
const track = document.querySelector("[data-carousel]");
if (track) {
  const prev = document.querySelector("[data-carousel-prev]");
  const next = document.querySelector("[data-carousel-next]");
  const step = () => (track.firstElementChild?.offsetWidth || 300) + 16;  // 一張卡片 + 間距

  const update = () => {
    if (!prev) return;
    prev.disabled = track.scrollLeft <= 4;
    next.disabled = track.scrollLeft + track.clientWidth >= track.scrollWidth - 4;
  };
  prev?.addEventListener("click", () => track.scrollBy({ left: -step(), behavior: "smooth" }));
  next?.addEventListener("click", () => track.scrollBy({ left: step(), behavior: "smooth" }));
  track.addEventListener("scroll", update, { passive: true });
  window.addEventListener("resize", update);
  update();

  // 鍵盤：焦點在櫥窗上時，左右鍵切換
  track.addEventListener("keydown", (event) => {
    if (event.key === "ArrowRight") { event.preventDefault(); track.scrollBy({ left: step(), behavior: "smooth" }); }
    if (event.key === "ArrowLeft") { event.preventDefault(); track.scrollBy({ left: -step(), behavior: "smooth" }); }
  });

  // 網址是 #post-12（剛發完文）時，捲到那一張
  const target = location.hash.startsWith("#post-") && document.querySelector(location.hash);
  if (target && track.contains(target)) {
    track.scrollLeft = target.offsetLeft - track.offsetLeft - 16;
    target.classList.add("ring-2", "ring-marker");
  }

  // 被截斷的文字才顯示「看全文」
  track.querySelectorAll("[data-post-body]").forEach((body) => {
    const more = body.nextElementSibling;
    if (body.scrollHeight > body.clientHeight + 2) more.hidden = false;
    more.addEventListener("click", () => {
      const open = body.classList.toggle(body.dataset.clamp) === false;
      more.textContent = open ? "收合" : "看全文";
    });
  });
}
