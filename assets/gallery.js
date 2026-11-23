// Left/right arrow keys move between photos on a photo page.
document.addEventListener("keydown", (ev) => {
  if (ev.altKey || ev.ctrlKey || ev.metaKey || ev.shiftKey) return;
  if (/^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement?.tagName || "")) return;
  const rel = ev.key === "ArrowLeft" ? "prev" : ev.key === "ArrowRight" ? "next" : null;
  const link = rel && document.querySelector(`.pager a[rel="${rel}"]`);
  if (link) location.href = link.href;
});

// A sideways swipe on the photo does the same on phones.
const frame = document.querySelector(".photo-frame");
let start = null;
frame?.addEventListener("touchstart", (ev) => {
  start = ev.touches.length === 1 ? ev.touches[0] : null;
}, { passive: true });
frame?.addEventListener("touchend", (ev) => {
  if (!start) return;
  const dx = ev.changedTouches[0].clientX - start.clientX;
  const dy = ev.changedTouches[0].clientY - start.clientY;
  start = null;
  if (Math.abs(dx) < 50 || Math.abs(dx) < Math.abs(dy) * 1.5) return;
  const link = document.querySelector(`.pager a[rel="${dx < 0 ? "next" : "prev"}"]`);
  if (link) location.href = link.href;
});
