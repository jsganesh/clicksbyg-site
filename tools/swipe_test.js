// Swipe check for assets/gallery.js, run against a fake page:
//   node tools/swipe_test.js assets/gallery.js
const fs = require("fs");
const src = fs.readFileSync(process.argv[2], "utf8");
function run(start, end) {
  const handlers = {};
  const frame = { addEventListener: (t, fn) => (handlers[t] = fn) };
  const links = { next: { href: "/photo/next/" }, prev: { href: "/photo/prev/" } };
  const location = { href: "/photo/here/" };
  const document = {
    addEventListener() {}, activeElement: null,
    querySelector: (q) => q === ".photo-frame" ? frame : links[(q.match(/rel="(\w+)"/) || [])[1]] || null,
  };
  new Function("document", "location", src)(document, location);
  handlers.touchstart({ touches: [{ clientX: start[0], clientY: start[1] }] });
  handlers.touchend({ changedTouches: [{ clientX: end[0], clientY: end[1] }] });
  return location.href;
}
const cases = [
  [[300, 200], [150, 210], "/photo/next/"],   // swipe left
  [[100, 200], [260, 190], "/photo/prev/"],   // swipe right
  [[200, 100], [180, 400], "/photo/here/"],   // scroll down
  [[200, 200], [180, 205], "/photo/here/"],   // small tap wobble
];
let ok = true;
for (const [a, b, want] of cases) {
  const got = run(a, b);
  if (got !== want) { ok = false; console.log("FAIL", a, b, got, "want", want); }
}
console.log(ok ? "swipe ok: 4 cases" : "swipe FAILED");
process.exit(ok ? 0 : 1);
