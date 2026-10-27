// Record the MealSenseAI demo tour as a 1080p video, scene by scene.
//
//   BASE=http://127.0.0.1:8380 OUT=out node demo/record.mjs
//
// Each scene lasts as long as its narration line (clips/durations.json, made
// first by voice.py speak), or an estimate from its word count; if an action
// takes longer, the scene runs long, and the real start of every scene goes to
// scenes.json, which voice.py uses to place each line. Nothing is staged: the
// meals are the seeded demo account's, and every result comes from the running
// model and rules. Wei Ming is fictional.
import { chromium } from "playwright";
import { existsSync, mkdirSync, readFileSync, renameSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const BASE = process.env.BASE ?? "http://127.0.0.1:8380";
const OUT = resolve(process.env.OUT ?? join(here, "out"));
const THEME = process.env.THEME ?? "light";
const PHOTOS = resolve(process.env.PHOTOS ?? join(here, "photos"));
const EMAIL = "weiming@mealsense.example";
const PASSWORD = "demo-mealsense-2026";
const LUNCH = join(PHOTOS, "chicken_rice.jpg");
const narration = JSON.parse(readFileSync(join(here, "narration.json"), "utf8")).scenes;
const plan = Object.fromEntries(narration.map((s) => [s.id, { ...s, seconds: s.text.split(/\s+/).length / 2.35 + 1 }]));
try {
  const spoken = JSON.parse(readFileSync(join(here, "clips", "durations.json"), "utf8")).seconds;
  for (const [id, secs] of Object.entries(spoken)) if (plan[id]) plan[id].seconds = Math.max(3, secs + 0.8);
  console.log("scene lengths follow the narration (clips/durations.json)");
} catch {
  console.log("no clips/durations.json: scene lengths estimated from the words");
}
if (!existsSync(LUNCH)) throw new Error(`No lunch photo at ${LUNCH}; run photos.py first (run.sh does).`);
const dataUrl = (p) => `data:image/jpeg;base64,${readFileSync(p).toString("base64")}`;

mkdirSync(OUT, { recursive: true });
const W = 1920, H = 1080;

// A visible cursor, a chapter label and full-screen title cards, injected into every page.
// Video capture does not show the real pointer. Card elements with data-at="0.4" appear 40%
// of the way through their scene, roughly when the narration reaches them.
const overlay = () => {
  const style = document.createElement("style");
  style.textContent = `
    #demo-cursor { position: fixed; z-index: 2147483647; width: 22px; height: 22px; margin: -11px 0 0 -11px;
      border-radius: 50%; background: rgba(20,20,24,.25); border: 2px solid rgba(255,255,255,.95);
      box-shadow: 0 1px 6px rgba(0,0,0,.35); pointer-events: none; transition: transform .12s; left: -50px; top: -50px; }
    #demo-cursor.down { transform: scale(.7); background: rgba(13,148,136,.55); }
    #demo-chapter { position: fixed; z-index: 2147483646; left: 28px; bottom: 26px; padding: 9px 16px; border-radius: 999px;
      font: 600 17px Inter, system-ui, sans-serif; color: #fff; background: rgba(15,23,42,.78); backdrop-filter: blur(6px);
      opacity: 0; transition: opacity .5s; pointer-events: none; }
    #demo-card { position: fixed; inset: 0; z-index: 2147483645; display: flex; flex-direction: column; align-items: center;
      justify-content: center; gap: 22px; padding: 0 140px; text-align: center;
      background: radial-gradient(ellipse at 50% 35%, #0f766e 0%, #0b3b3a 55%, #071d1f 100%);
      color: #f0fdfa; font-family: Inter, system-ui, sans-serif; opacity: 0; transition: opacity .7s; pointer-events: none; }
    #demo-card .logo { width: 104px; height: 104px; }
    #demo-card h1 { margin: 0; font-size: 64px; line-height: 1.1; font-weight: 800; letter-spacing: -.01em; }
    #demo-card h2 { margin: 0; font-size: 46px; line-height: 1.15; font-weight: 750; }
    #demo-card p { margin: 0; font-size: 27px; color: #ccfbf1; }
    #demo-card small { font-size: 17px; color: #99f6e4; opacity: .85; }
    #demo-card .row { display: flex; gap: 28px; justify-content: center; align-items: stretch; margin-top: 10px; }
    #demo-card .tile { width: 330px; padding: 26px 24px; border-radius: 22px; background: rgba(240,253,250,.08);
      border: 1px solid rgba(153,246,228,.25); text-align: left; }
    #demo-card .tile b { display: block; font-size: 52px; font-weight: 800; color: #5eead4; line-height: 1; }
    #demo-card .tile span { display: block; margin-top: 12px; font-size: 21px; color: #f0fdfa; line-height: 1.3; }
    #demo-card .tile i { display: block; margin-top: 10px; font-style: normal; font-size: 14px; color: #99f6e4; opacity: .8; }
    #demo-card .versus { display: flex; gap: 70px; align-items: center; margin-top: 8px; }
    #demo-card .label { width: 300px; padding: 18px 20px; background: #fff; color: #0f172a; border-radius: 10px; text-align: left;
      font: 600 17px Inter, system-ui, sans-serif; box-shadow: 0 10px 40px rgba(0,0,0,.35); }
    #demo-card .label h3 { margin: 0 0 8px; font-size: 25px; font-weight: 900; border-bottom: 8px solid #0f172a; padding-bottom: 6px; }
    #demo-card .label div { display: flex; justify-content: space-between; border-bottom: 1px solid #cbd5e1; padding: 6px 0; }
    #demo-card .plate { position: relative; width: 520px; height: 390px; border-radius: 22px; overflow: hidden; box-shadow: 0 10px 40px rgba(0,0,0,.4); }
    #demo-card .plate img { width: 100%; height: 100%; object-fit: cover; }
    #demo-card .q { position: absolute; padding: 8px 16px; border-radius: 999px; background: rgba(15,23,42,.82); color: #fff;
      font: 700 22px Inter, system-ui, sans-serif; }
    #demo-card .pains { display: grid; grid-template-columns: repeat(3, 330px); gap: 28px; margin-top: 10px; }
    #demo-card .pains .tile b { font-size: 34px; color: #fff; }
    #demo-card [data-at] { opacity: 0; transform: translateY(18px); transition: opacity .6s, transform .6s; }
    #demo-card [data-at].in { opacity: 1; transform: none; }`;
  const mount = () => {
    if (document.getElementById("demo-cursor")) return;
    document.head.appendChild(style);
    const cursor = Object.assign(document.createElement("div"), { id: "demo-cursor" });
    const chapter = Object.assign(document.createElement("div"), { id: "demo-chapter" });
    const card = Object.assign(document.createElement("div"), { id: "demo-card" });
    document.body.append(cursor, chapter, card);
    addEventListener("mousemove", (e) => { cursor.style.left = e.clientX + "px"; cursor.style.top = e.clientY + "px"; }, true);
    addEventListener("mousedown", () => cursor.classList.add("down"), true);
    addEventListener("mouseup", () => cursor.classList.remove("down"), true);
    const saved = sessionStorage.getItem("demo-chapter");
    if (saved) { chapter.textContent = saved; chapter.style.opacity = "1"; }
  };
  window.__demo = {
    chapter(text) {
      sessionStorage.setItem("demo-chapter", text || "");
      const el = document.getElementById("demo-chapter");
      if (!el) return;
      el.style.opacity = "0";
      setTimeout(() => { el.textContent = text; el.style.opacity = text ? "1" : "0"; }, 250);
    },
    card(html, seconds) {
      const el = document.getElementById("demo-card");
      if (!el) return;
      if (html) {
        el.innerHTML = html;
        for (const part of el.querySelectorAll("[data-at]")) {
          setTimeout(() => part.classList.add("in"), Math.max(150, Number(part.dataset.at) * seconds * 1000));
        }
      }
      el.style.opacity = html ? "1" : "0";
    },
  };
  if (document.body) mount(); else addEventListener("DOMContentLoaded", mount);
};

const browser = await chromium.launch(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {});
const context = await browser.newContext({
  viewport: { width: W, height: H },
  deviceScaleFactor: 1,
  colorScheme: THEME,
  timezoneId: "Asia/Singapore",
  locale: "en-SG",
  recordVideo: { dir: OUT, size: { width: W, height: H } },
});
await context.addInitScript(overlay);
// Wei Ming has used the app for a week: the first-run checklist is long dismissed.
await context.addInitScript((theme) => {
  try { localStorage.setItem("mealsense.theme", theme); localStorage.setItem("mealsense.gs.dismissed", "1"); } catch {}
}, THEME);

// Each take starts from the seeded week: anything after today's breakfast and any unsaved meal from an earlier take go,
// and so does the Meal Advisor's general conversation.
const signIn = await context.request.post(`${BASE}/api/v1/auth/login`, { data: { email: EMAIL, password: PASSWORD } });
if (!signIn.ok()) throw new Error(`Demo sign-in failed (${signIn.status()}); run demo/seed.py first.`);
const token = (await signIn.json()).access_token;
const auth = { Authorization: `Bearer ${token}` };
const today = new Date().toLocaleDateString("en-CA", { timeZone: "Asia/Singapore" });
const history = await (await context.request.get(`${BASE}/api/v1/meals/history?tz_offset_min=480`, { headers: auth })).json();
for (const m of history.meals ?? []) {
  const day = new Date(m.eaten_at).toLocaleDateString("en-CA", { timeZone: "Asia/Singapore" });
  if (m.status !== "confirmed" || (day === today && m.meal_type !== "breakfast")) {
    await context.request.delete(`${BASE}/api/v1/meals/${m.id}`, { headers: auth });
  }
}
const thread = await (await context.request.get(`${BASE}/api/v1/advisor/threads`, { headers: auth })).json().catch(() => ({}));
if (thread?.thread_id) await context.request.delete(`${BASE}/api/v1/advisor/threads/${thread.thread_id}`, { headers: auth });

const page = await context.newPage();
const t0 = Date.now();
const log = [];
const pause = (ms) => page.waitForTimeout(ms);

let pointer = { x: W / 2, y: H / 2 };
async function moveTo(x, y, steps = 28) {
  await page.mouse.move(x, y, { steps });
  pointer = { x, y };
}
async function point(locator, { click = true, dx = 0, dy = 0 } = {}) {
  await locator.scrollIntoViewIfNeeded({ timeout: 5000 }).catch(() => {});
  const box = await locator.boundingBox({ timeout: 5000 }).catch(() => null);
  if (!box) return false;
  await moveTo(box.x + box.width / 2 + dx, box.y + box.height / 2 + dy);
  await pause(250);
  if (click) await page.mouse.click(pointer.x, pointer.y);
  return true;
}
const chapter = (text) => page.evaluate((t) => window.__demo?.chapter(t), text);
const card = (html, seconds = 0) => page.evaluate(([h, s]) => window.__demo?.card(h, s), [html, seconds]);
async function scroll(by, steps = 14) {
  for (let i = 0; i < steps; i++) { await page.mouse.wheel(0, by / steps); await pause(55); }
}
async function bringIntoView(locator, top = 110) {  // scroll smoothly until the element sits near the top
  const box = await locator.boundingBox({ timeout: 5000 }).catch(() => null);
  if (box) await scroll(box.y - top, 16);
}
async function open(title) {  // a collapsible card on the meal page, by its title
  const button = page.locator("section > button", { hasText: title }).first();
  await bringIntoView(button);
  if ((await button.getAttribute("aria-expanded")) !== "true") await point(button);
  else await point(button, { click: false });
  return button.locator("xpath=..");
}

async function scene(id, run) {
  const s = plan[id];
  const start = Date.now();
  log.push({ id, start: (start - t0) / 1000, planned: s.seconds });
  console.log(`[${((start - t0) / 1000).toFixed(1)}s] ${id}`);
  try {
    await run(s.seconds);
  } catch (error) {
    console.warn(`   ${id}: ${error.message.split("\n")[0]}`);
  }
  const left = s.seconds * 1000 - (Date.now() - start);
  if (left > 0) await pause(left);
  log[log.length - 1].actual = (Date.now() - start) / 1000;
}

// The opening runs over title cards on the landing page, signed out.
await page.goto(`${BASE}/`);
await page.waitForLoadState("networkidle");

await scene("hook", async (secs) => {
  await card(`
    <h1 data-at="0">Most meals don't come with a label.</h1>
    <div class="versus">
      <div class="label" data-at="0.18"><h3>Nutrition Facts</h3><div><span>Serving</span><span>3 biscuits</span></div>
        <div><span>Energy</span><span>140 kcal</span></div><div><span>Carbohydrate</span><span>19 g</span></div>
        <div><span>Sugars</span><span>8 g</span></div></div>
      <div class="plate" data-at="0.36"><img src="${dataUrl(LUNCH)}" alt="">
        <span class="q" style="left:24px;top:22px">? kcal</span><span class="q" style="right:24px;top:84px">? g carbs</span>
        <span class="q" style="left:60px;bottom:30px">? portion</span></div>
    </div>
    <small data-at="0.5">Illustrative label. Photo: Wikimedia Commons (credits in the description).</small>`, secs);
});

await scene("pain", async (secs) => {
  await card(`
    <h2 data-at="0">So people guess.</h2>
    <div class="pains">
      <div class="tile" data-at="0.12"><b>What is it?</b><span>Mixed dishes are hard to break down into foods.</span></div>
      <div class="tile" data-at="0.4"><b>How much?</b><span>Portions change from stall to stall.</span></div>
      <div class="tile" data-at="0.55"><b>So what?</b><span>Even good numbers are hard to act on.</span></div>
    </div>
    <p data-at="0.75">Logging every meal by hand is tedious, so most people stop.</p>`, secs);
});

await scene("stakes", async (secs) => {
  await card(`
    <h2 data-at="0">Why it matters now</h2>
    <div class="row">
      <div class="tile" data-at="0.06"><b>~830M</b><span>people living with diabetes worldwide</span><i>WHO, 2022</i></div>
      <div class="tile" data-at="0.2"><b>1 in 12</b><span>adults in Singapore living with diabetes</span><i>MOH, 2023</i></div>
      <div class="tile" data-at="0.33"><b>Up to 1M</b><span>Singapore residents by 2050, without effective prevention</span><i>MOH projection</i></div>
      <div class="tile" data-at="0.5"><b>−18%</b><span>household sugar from pre-packed drinks after Nutri-Grade</span><i>Before-and-after study</i></div>
    </div>
    <p data-at="0.82">Labels reach the bottle and the box. Not the plate.</p>`, secs);
});

await scene("meet", async () => {
  await card("");
  await pause(1400);
  await moveTo(960, 520);
  await pause(Math.max(0, plan.meet.seconds * 1000 * 0.45 - 1400));
  await scroll(620, 20);
  await pause(2500);
});

await scene("dashboard", async () => {
  // Signed in as Wei Ming from here on.
  await page.evaluate((t) => localStorage.setItem("msai_token", t), token);
  await page.goto(`${BASE}/profile`);
  await page.waitForLoadState("networkidle");
  await chapter("Health profile");
  await pause(600);
  const diabetes = page.getByText(/type 2/i).first();
  await point(diabetes, { click: false });
  await pause(Math.max(2500, plan.dashboard.seconds * 1000 * 0.3));
  await point(page.getByRole("link", { name: "Dashboard", exact: true }).first());
  await page.waitForURL(`${BASE}/`);
  await chapter("Dashboard");
  await page.getByText("7-day calories").waitFor({ timeout: 15000 });
  await pause(800);
  for (const name of ["Calories today", "Carbohydrates"]) {
    await point(page.getByText(name, { exact: true }).first(), { click: false });
    await pause(900);
  }
  await scroll(420);
  await pause(1200);
  await point(page.getByText("Today's macro energy"), { click: false });
  await pause(1500);
});

await scene("capture", async () => {
  await scroll(-900, 8);
  await point(page.getByRole("link", { name: "Capture Meal" }).last());
  await page.waitForURL(/capture/);
  await chapter("Capture");
  await pause(1200);
  // The file chooser is the phone's camera roll; the photo lands in the Top view slot.
  await page.locator('input[type="file"]').nth(1).setInputFiles(LUNCH);
  await pause(1800);
  await point(page.getByRole("button", { name: /ANALYZE MEAL/ }));
  await page.getByRole("button", { name: /New capture/ }).waitFor({ timeout: 90000 });
  await pause(1200);
  await scroll(-600, 6);
  // The ten pipeline steps, with what each one did.
  if (await point(page.getByRole("button", { name: "Open analysis telemetry" }))) {
    await pause(Math.max(3500, plan.capture.seconds * 1000 * 0.3));
    await point(page.getByRole("button", { name: "Close", exact: true }).first());
  }
  await pause(400);
  await point(page.getByRole("button", { name: /^lunch$/i }).first());
});

await scene("review", async () => {
  await chapter("Review");
  await pause(500);
  const card1 = page.getByRole("button", { name: /Why\? Show how this was estimated/ }).first();
  const name = page.locator("text=/\\d+ g · \\d+ kcal/").first();
  await point(name, { click: false });
  await pause(2500);
  await point(card1);
  await pause(3500);
  for (const label of ["Confirm", "Rename", "Portion"]) {
    await point(page.getByRole("button", { name: label, exact: true }).first(), { click: false });
    await pause(900);
  }
  await point(card1);  // hide the details again
  await pause(800);
});

await scene("meaning", async (secs) => {
  await chapter("What it means");
  await bringIntoView(page.getByText("Key takeaways").first(), 130);
  await pause(Math.max(2500, secs * 1000 * 0.3));
  await open("Glucose, energy & tips");
  await pause(Math.max(2500, secs * 1000 * 0.25));
  const advisory = await open("Meal advisory");
  await pause(1500);
  await bringIntoView(advisory, 120);
  await pause(1500);
});

await scene("portion", async () => {
  await chapter("Portion simulator");
  const sim = await open("Portion simulator");
  await pause(1500);
  const slider = sim.locator('input[type="range"]').first();
  await slider.scrollIntoViewIfNeeded().catch(() => {});
  await scroll(-120, 4);
  const box = await slider.boundingBox();
  if (box) {
    const value = Number(await slider.inputValue()), max = Number(await slider.getAttribute("max")) || 1;
    const y = box.y + box.height / 2;
    const at = box.x + box.width * (value / max);
    await moveTo(at, y);
    await page.mouse.down();
    await moveTo(at - box.width * 0.18, y, 40);  // about two thirds of the original portion
    await page.mouse.up();
  }
  await pause(2500);
  await point(sim.locator("table").first(), { click: false });
  await pause(2500);
  await bringIntoView(sim.getByText(/Estimate range|Modified meal/).first(), 380);
  await pause(2500);
  const reset = sim.getByRole("button", { name: /Reset/ });
  if (await reset.count()) await point(reset);
});

await scene("whatif", async (secs) => {
  await chapter("What if I walk?");
  const forecast = await open("Forecast & what-if");
  await pause(1200);
  await bringIntoView(forecast.getByText("What if I exercise?").first(), 120);
  await pause(1500);
  const walk = forecast.getByRole("slider").first();
  await point(walk, { click: false });
  await pause(1500);
  await scroll(520);
  await pause(Math.max(2500, secs * 1000 * 0.3));
  await scroll(420);
  await pause(1800);
  // Lunch is saved before moving on, as Wei Ming would.
  await scroll(-4000, 10);
  await point(page.getByRole("button", { name: /Save meal/ }).first());
  await page.waitForURL(/\/meals\/\d+/, { timeout: 15000 }).catch(() => {});
  await pause(1200);
});

await scene("advisor", async () => {
  await point(page.getByRole("link", { name: "Meal Advisor", exact: true }).first());
  await page.waitForURL(/advisor/);
  await chapter("Meal Advisor");
  await pause(1500);
  await point(page.getByRole("button", { name: "How was my week?", exact: true }).first());
  await page.getByText(/sources?\s*▾/).first().waitFor({ timeout: 60000 }).catch(() => {});
  await pause(3500);
  const sources = page.getByText(/sources?\s*▾/).first();
  if (await point(sources)) await pause(3500);
});

await scene("insights", async () => {
  await point(page.getByRole("link", { name: "Nutrition Insights", exact: true }).first());
  await page.waitForURL(/insights/);
  await chapter("Nutrition Insights");
  await pause(2000);
  await point(page.getByText("Macronutrients per day (g)"), { click: false });
  await pause(1500);
  await scroll(480);
  await pause(2000);
});

await scene("outro", async (secs) => {
  await chapter("");
  await card(`
    <img class="logo" data-at="0" src="/favicon.svg" alt="">
    <h1 data-at="0.05">MealSenseAI</h1>
    <p data-at="0.55">Understand your food. Make healthier choices.</p>
    <small data-at="0.6">Wei Ming is fictional. Educational estimates only, not medical advice.<br>Meal photos from Wikimedia Commons under free licences; credits in the description.</small>`, secs);
});

const video = page.video();
await context.close();
await browser.close();
const path = await video.path();
renameSync(path, join(OUT, "demo.webm"));
writeFileSync(join(OUT, "scenes.json"), JSON.stringify({ base: BASE, theme: THEME, scenes: log }, null, 1));
console.log(`video: ${join(OUT, "demo.webm")}`);
for (const s of log) if (s.actual > s.planned + 0.5) console.log(`   ${s.id} ran ${s.actual.toFixed(1)}s (planned ${s.planned.toFixed(1)}s)`);
