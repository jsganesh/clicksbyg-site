// Left/right arrow keys move between photos on a photo page.
document.addEventListener("keydown", (ev) => {
  if (ev.altKey || ev.ctrlKey || ev.metaKey || ev.shiftKey) return;
  if (/^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement?.tagName || "")) return;
  const rel = ev.key === "ArrowLeft" ? "prev" : ev.key === "ArrowRight" ? "next" : null;
  const link = rel && document.querySelector(`.pager a[rel="${rel}"]`);
  if (link) location.href = link.href;
});
