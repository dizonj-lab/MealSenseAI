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
const SCRIPT = process.env.NARRATION ?? "narration.json";   // narration-full.json: the 12-minute presentation
const narration = JSON.parse(readFileSync(join(here, SCRIPT), "utf8")).scenes;
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
// Report figures (docs/report/charts), drawn from the training evidence in ml/models/exp002/evidence/training.
const chart = (f) => `data:image/png;base64,${readFileSync(join(here, "..", "docs", "report", "charts", f)).toString("base64")}`;

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
    #demo-card .tiers { display: grid; grid-template-columns: repeat(3, 400px); gap: 28px; margin-top: 10px; }
    #demo-card .tiers .tile b { font-size: 44px; } #demo-card .tiers .tile em { display: block; margin-top: 6px; font-style: normal; font-size: 19px; color: #99f6e4; }
    #demo-card .tiers .tile ul { margin: 14px 0 0; padding-left: 20px; font-size: 19px; line-height: 1.5; color: #f0fdfa; }
    #demo-card .tiers .tile.hi { border-color: #5eead4; background: rgba(94,234,212,.12); }
    #demo-card .arch { display: flex; align-items: center; gap: 18px; margin-top: 12px; }
    #demo-card .box { padding: 18px 20px; min-width: 190px; border-radius: 16px; background: rgba(240,253,250,.08); border: 1px solid rgba(153,246,228,.35);
      text-align: left; font-size: 18px; line-height: 1.35; color: #ccfbf1; }
    #demo-card .box b { display: block; font-size: 23px; color: #fff; margin-bottom: 4px; }
    #demo-card .box.side { border-style: dashed; }
    #demo-card .arrow { font-size: 34px; color: #5eead4; }
    #demo-card .steps { display: grid; grid-template-columns: repeat(5, 290px); gap: 16px; margin-top: 10px; }
    #demo-card .steps div { padding: 14px 16px; border-radius: 14px; background: rgba(240,253,250,.08); border: 1px solid rgba(153,246,228,.25);
      text-align: left; font-size: 20px; color: #fff; }
    #demo-card .steps div i { display: block; font-style: normal; font-size: 15px; color: #99f6e4; margin-top: 4px; }
    #demo-card .steps div span { color: #5eead4; font-weight: 800; margin-right: 8px; }
    #demo-card .two { display: grid; grid-template-columns: 640px 760px; gap: 40px; text-align: left; margin-top: 8px; }
    #demo-card .two ul { margin: 0; padding-left: 22px; font-size: 22px; line-height: 1.6; color: #f0fdfa; }
    #demo-card .metrics { display: grid; grid-template-columns: repeat(2, 1fr); gap: 18px; }
    #demo-card .metrics .tile { width: auto; padding: 18px 20px; } #demo-card .metrics .tile b { font-size: 44px; }
    #demo-card .eq { font: 600 40px "STIX Two Math", Georgia, serif; color: #fff; padding: 18px 34px; border-radius: 16px; background: rgba(240,253,250,.08); }
    #demo-card .charts.big img { height: 640px; max-width: 1640px; }
    #demo-card .charts.two img { height: 560px; max-width: 800px; }
    #demo-card .charts.three img { height: 430px; max-width: 590px; }
    #demo-card .charts { display: flex; gap: 28px; justify-content: center; margin-top: 6px; }
    #demo-card .charts img { height: 400px; max-width: 820px; object-fit: contain; background: #fff; border-radius: 16px; padding: 12px; }
    #demo-card .row.small .tile { width: 300px; padding: 18px 20px; } #demo-card .row.small .tile b { font-size: 40px; }
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
      const cursor = document.getElementById("demo-cursor");   // no pointer over a title card
      if (cursor) cursor.style.opacity = html ? "0" : "1";
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
// Picture-in-picture scripts: keep cards and figures clear of the presenter's corner (bottom right, ~520 × 300 px).
if (narration.some((s) => s.mode === "pip")) await context.addInitScript(() => {
  const style = () => {
    const el = document.createElement("style");
    el.textContent = `#demo-card { padding: 0 560px 150px 90px !important; }
      #demo-card .charts.big img { max-width: 1240px !important; height: 600px !important; }
      #demo-card .charts.two img { max-width: 610px !important; height: 480px !important; }
      #demo-card .charts.three img { max-width: 395px !important; height: 360px !important; }
      #demo-card .charts img { max-width: 1240px !important; } #demo-card .row.small .tile { width: 270px !important; }`;
    document.head.appendChild(el);
  };
  if (document.head) style(); else document.addEventListener("DOMContentLoaded", style);
});
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

// Scenes by id; narration.json (or NARRATION) decides which run, in its order.
const SCENES = {};

SCENES.hook = async (secs) => {
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
};

SCENES.pain = async (secs) => {
  await card(`
    <h2 data-at="0">So people guess.</h2>
    <div class="pains">
      <div class="tile" data-at="0.12"><b>What is it?</b><span>Mixed dishes are hard to break down into foods.</span></div>
      <div class="tile" data-at="0.4"><b>How much?</b><span>Portions change from stall to stall.</span></div>
      <div class="tile" data-at="0.55"><b>So what?</b><span>Even good numbers are hard to act on.</span></div>
    </div>
    <p data-at="0.75">Logging every meal by hand is tedious, so most people stop.</p>`, secs);
};

SCENES.stakes = async (secs) => {
  await card(`
    <h2 data-at="0">Why it matters now</h2>
    <div class="row">
      <div class="tile" data-at="0.06"><b>~830M</b><span>people living with diabetes worldwide</span><i>WHO, 2022</i></div>
      <div class="tile" data-at="0.2"><b>1 in 12</b><span>adults in Singapore living with diabetes</span><i>MOH, 2023</i></div>
      <div class="tile" data-at="0.33"><b>Up to 1M</b><span>Singapore residents by 2050, without effective prevention</span><i>MOH projection</i></div>
      <div class="tile" data-at="0.5"><b>−18%</b><span>household sugar from pre-packed drinks after Nutri-Grade</span><i>Before-and-after study</i></div>
    </div>
    <p data-at="0.82">Labels reach the bottle and the box. Not the plate.</p>`, secs);
};

SCENES.meet = async () => {
  await card("");
  await pause(1400);
  await moveTo(960, 520);
  await pause(Math.max(0, plan.meet.seconds * 1000 * 0.45 - 1400));
  await scroll(620, 20);
  await pause(2500);
};

SCENES.dashboard = async () => {
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
};

SCENES.capture = async () => {
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
};

SCENES.review = async () => {
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
};

SCENES.meaning = async (secs) => {
  await chapter("What it means");
  await open("Key takeaways");   // collapsed since 0.13.4
  await pause(Math.max(2500, secs * 1000 * 0.3));
  await open("Glucose, energy & tips");
  await pause(Math.max(2500, secs * 1000 * 0.25));
  const advisory = await open("Meal advisory");
  await pause(1500);
  await bringIntoView(advisory, 120);
  await pause(1500);
};

SCENES.portion = async () => {
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
};

SCENES.whatif = async (secs) => {
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
};

SCENES.advisor = async () => {
  await point(page.getByRole("link", { name: "Meal Advisor", exact: true }).first());
  await page.waitForURL(/advisor/);
  await chapter("Meal Advisor");
  await pause(1500);
  await point(page.getByRole("button", { name: "How was my week?", exact: true }).first());
  await page.getByText(/sources?\s*▾/).first().waitFor({ timeout: 60000 }).catch(() => {});
  await pause(3500);
  const sources = page.getByText(/sources?\s*▾/).first();
  if (await point(sources)) await pause(3500);
};

SCENES.insights = async () => {
  await point(page.getByRole("link", { name: "Nutrition Insights", exact: true }).first());
  await page.waitForURL(/insights/);
  await chapter("Nutrition Insights");
  await pause(2000);
  await point(page.getByText("Macronutrients per day (g)"), { click: false });
  await pause(1500);
  await scroll(480);
  await pause(2000);
};

SCENES.outro = async (secs) => {
  await chapter("");
  await card(`
    <img class="logo" data-at="0" src="/favicon.svg" alt="">
    <h1 data-at="0.05">MealSenseAI</h1>
    <p data-at="0.55">Understand your food. Make healthier choices.</p>
    <small data-at="0.6">Wei Ming is fictional. Educational estimates only, not medical advice.<br>Meal photos from Wikimedia Commons under free licences; credits in the description.</small>`, secs);
};


// ---- The 12-minute presentation (narration-full.json): business case, pricing and system design cards.
const SRC = (t) => `<i>${t}</i>`;

SCENES.burden = async (secs) => {
  await card(`
    <h2 data-at="0">Why it matters</h2>
    <div class="row">
      <div class="tile" data-at="0.08"><b>~830M</b><span>people living with diabetes worldwide</span>${SRC("WHO, 2022")}</div>
      <div class="tile" data-at="0.25"><b>1 in 12</b><span>adults in Singapore</span>${SRC("MOH, 2023")}</div>
      <div class="tile" data-at="0.4"><b>Up to 1M</b><span>Singapore residents by 2050, without effective prevention</span>${SRC("MOH projection")}</div>
      <div class="tile" data-at="0.6"><b>S$1B → 2.5B</b><span>yearly cost to Singapore, 2010 → 2050, most of it lost productivity</span>${SRC("Png et al., BMC Public Health 2016")}</div>
    </div>`, secs);
};

SCENES.gap = async (secs) => {
  await card(`
    <h2 data-at="0">Visibility changes choices. The plate is still invisible.</h2>
    <div class="row">
      <div class="tile" data-at="0.1"><b>−18%</b><span>household sugar from pre-packed drinks after Nutri-Grade</span>${SRC("Before-and-after study")}</div>
      <div class="tile" data-at="0.4"><b>Labels</b><span>reach the bottle and the box, not the hawker plate</span></div>
      <div class="tile" data-at="0.55"><b>Apps</b><span>count calories or search a food list</span></div>
      <div class="tile" data-at="0.7"><b>Missing</b><span>what this plate may do to your glucose, and how sure that is</span></div>
    </div>`, secs);
};

SCENES.value = async (secs) => {
  await card(`
    <h2 data-at="0">MealSenseAI</h2>
    <div class="pains">
      <div class="tile" data-at="0.12"><b>One photo</b><span>becomes foods, portions and nutrition.</span></div>
      <div class="tile" data-at="0.35"><b>Meaning</b><span>glucose impact, glycaemic load and a practical next step.</span></div>
      <div class="tile" data-at="0.45"><b>Honest</b><span>every estimate shows its range and source. You confirm.</span></div>
    </div>
    <small data-at="0.72">For anyone, with or without a health condition: wellness, weight, heart health, balanced eating. Diabetes first, where the need is sharpest.</small>`, secs);
};

SCENES.mark = async () => {
  await card("");
  await chapter("Mark a missed food");
  const before = await page.locator('[id^="food-"]').evaluateAll((els) => els.map((e) => e.id));
  const mark = page.getByRole("button", { name: /Mark it on the photo/ }).first();
  await bringIntoView(mark, 300);
  await point(mark);
  const area = page.locator('[data-testid="draw-area"]').first();
  await area.waitFor({ timeout: 5000 });
  await scroll(-400, 6);
  await pause(1500);
  const box = await area.boundingBox();
  if (box) {   // drag a box over the lower right of the plate, as a finger would
    await moveTo(box.x + box.width * 0.58, box.y + box.height * 0.55);
    await page.mouse.down();
    await moveTo(box.x + box.width * 0.86, box.y + box.height * 0.86, 45);
    await page.mouse.up();
  }
  await page.waitForFunction((ids) => [...document.querySelectorAll('[id^="food-"]')].some((e) => !ids.includes(e.id)),
    before, { timeout: 20000 }).catch(() => {});
  await pause(1800);
  const fresh = (await page.locator('[id^="food-"]').evaluateAll((els, ids) => els.map((e) => e.id).filter((i) => !ids.includes(i)), before))[0];
  if (fresh) {
    const item = page.locator(`#${fresh}`);
    await point(item, { click: false });
    await pause(1500);
    // Unsure? Name it from the model's own guesses: a tap, and it is remembered next time.
    const guess = item.locator("button:has-text('%')").first();
    if (await guess.count()) { await point(guess); await pause(2000); }
  }
  await scroll(-2000, 8);
  await pause(800);
};

SCENES.pricing = async (secs) => {
  await chapter("");
  await card(`
    <h2 data-at="0">Pricing <small style="font-size:22px">(freemium, as proposed; to validate in the trial)</small></h2>
    <div class="tiers">
      <div class="tile" data-at="0.08"><b>Free</b><em>S$0</em><ul><li>Photo and text meal logging</li><li>Nutrition per meal and day</li><li>History and trends</li></ul></div>
      <div class="tile hi" data-at="0.3"><b>Subscription</b><em>S$3.99/month Singapore · S$2.99 ASEAN</em><ul><li>Glucose impact and glycaemic load</li><li>Meal Advisor</li><li>Portion and activity simulators, your own readings</li></ul></div>
      <div class="tile" data-at="0.78"><b>Organisations</b><em>later, per member</em><ul><li>Clinics, employers, insurers</li><li>Same app for members</li><li>Priced with pilots</li></ul></div>
    </div>
    <small data-at="0.5">AI nutrition apps: Foodvisor, Cal AI, SnapCalorie, Healthify, about US$9–60/month (indicative, as in the proposal).</small>`, secs);
};

SCENES.design = async (secs) => {
  await card(`
    <h2 data-at="0">System design</h2>
    <div class="arch">
      <div class="box" data-at="0.1"><b>Browser</b>phone or desktop<br>React + TypeScript</div><div class="arrow" data-at="0.15">→</div>
      <div class="box" data-at="0.2"><b>Web server</b>nginx: the app,<br>/api proxy, rate limits</div><div class="arrow" data-at="0.25">→</div>
      <div class="box" data-at="0.3"><b>Backend</b>FastAPI · ONNX Runtime<br>EfficientNet-B0 + YOLO11n-seg<br>nutrition · insights · advisor</div><div class="arrow" data-at="0.45">→</div>
      <div class="box" data-at="0.45"><b>PostgreSQL 16</b>users, meals, foods,<br>corrections, logs</div>
    </div>
    <div class="arch" style="margin-top:4px">
      <div class="box side" data-at="0.6"><b>Ollama · Qwen 2.5 1.5B</b>local language model, wording only</div>
      <div class="box side" data-at="0.7"><b>Docker Compose</b>one server, CPU; photos and data in volumes</div>
    </div>
    <p data-at="0.85">No paid cloud AI in the loop.</p>`, secs);
};

SCENES.pipeline = async (secs) => {
  const steps = [["Capture", "your input"], ["Preprocess", "EXIF, resize"], ["Detect", "YOLO11n-seg"], ["Classify", "EfficientNet-B0, top 3"],
    ["Portion", "estimate ± band"], ["Nutrition", "exact · proxy · none"], ["Aggregate", "totals, GL"], ["Explain", "local SLM or rules"],
    ["Recommend", "rules, cited"], ["Review", "you confirm"]];
  await card(`<h2 data-at="0">Ten stages, all visible</h2><div class="steps">${steps.map(([t, d], i) =>
    `<div data-at="${(0.08 + i * 0.07).toFixed(2)}"><span>${i + 1}</span>${t}<i>${d}</i></div>`).join("")}</div>
    <p data-at="0.85">Model prediction · Estimate · Guidance · Your input: each labelled differently.</p>`, secs);
};

SCENES.vision = async (secs) => {
  await card(`
    <h2 data-at="0">Recognising the food</h2>
    <div class="two">
      <ul data-at="0.08"><li>EfficientNet-B0, ImageNet start</li><li>Food-101 + FoodSG: 320 classes</li><li>Transfer learning: last 3 blocks + head</li>
        <li>AdamW: lr 1e-5 backbone, 5e-5 head, weight decay 1e-4</li><li>Augmentation: crop, flip, rotate, colour</li><li>5 epochs, batch 32</li></ul>
      <div class="metrics">
        <div class="tile" data-at="0.45"><b>70.6%</b><span>top-1 accuracy</span>${SRC("45,800 test images")}</div>
        <div class="tile" data-at="0.5"><b>85.7%</b><span>top-3 accuracy</span>${SRC("macro-F1 66.7%")}</div>
        <div class="tile" data-at="0.7"><b>100%</b><span>same top 3 after ONNX export</span>${SRC("601 images")}</div>
        <div class="tile" data-at="0.78"><b>11.8 ms</b><span>per photo on CPU</span>${SRC("ONNX Runtime")}</div>
      </div>
    </div>`, secs);
};

SCENES.training = async (secs) => {
  await chapter("");
  await card(`
    <h2 data-at="0">How I trained the model</h2>
    <div class="row small">
      <div class="tile" data-at="0.03"><b>310,861</b><span>images: Food-101 + FoodSG-233</span>${SRC("4,193 removed: conflicting labels, duplicates")}</div>
      <div class="tile" data-at="0.16"><b>0</b><span>duplicate images across train and test</span>${SRC("SHA-256 audit")}</div>
      <div class="tile" data-at="0.24"><b>2 stages</b><span>frozen backbone, then last 3 blocks + head</span>${SRC("RTX 5060 Ti, ~20 min each")}</div>
      <div class="tile" data-at="0.62"><b>70.6% · 85.7%</b><span>top-1 · top-3 on 45,800 test images</span>${SRC("macro-F1 66.7%")}</div>
    </div>
    <div class="charts">
      <img data-at="0.36" src="${chart("11_training_curves.png")}" alt="">
      <img data-at="0.74" src="${chart("12_calibration.png")}" alt="">
    </div>`, secs);
};

SCENES.settings = async (secs) => {
  // Paced to the narration: recognition ~45%, language model ~35%, prompts the rest.
  const t0 = Date.now(), ms = secs * 1000;
  const until = async (share) => pause(Math.max(400, t0 + ms * share - Date.now()));
  await card("");
  await page.goto(`${BASE}/admin/settings`);
  await page.waitForLoadState("networkidle");
  await chapter("Admin · model settings");
  await page.getByText("Whole-photo suggestion threshold").first().waitFor({ timeout: 15000 });
  const steps = [["Whole-photo suggestion threshold", 0.17], ["Identify threshold", 0.27], ["Personal memory match", 0.45]];
  for (const [label, share] of steps) {
    await point(page.getByText(label, { exact: true }).first(), { click: false });
    await until(share);
  }
  await bringIntoView(page.getByText("Local language model", { exact: true }).first(), 120);
  for (const [label, share] of [["Preferred model", 0.6], ["Temperature", 0.7], ["Time limit per call", 0.8]]) {
    await point(page.getByText(label, { exact: true }).first(), { click: false });
    await until(share);
  }
  await page.goto(`${BASE}/admin/prompts`);
  await page.waitForLoadState("networkidle");
  await chapter("Admin · versioned prompts");
  await point(page.getByText(/History \(/).first(), { click: false });
  await until(0.97);
};

SCENES.multifood = async (secs) => {
  await card(`
    <h2 data-at="0">Several foods on one plate</h2>
    <div class="row">
      <div class="tile" data-at="0.3"><b>74.7%</b><span>detection precision</span>${SRC("IoU ≥ 0.5")}</div>
      <div class="tile" data-at="0.36"><b>68.4%</b><span>detection recall</span>${SRC("180 of 263 items")}</div>
      <div class="tile" data-at="0.45"><b>262 ms</b><span>per plate, median, CPU</span>${SRC("p95 320 ms")}</div>
      <div class="tile" data-at="0.7"><b>1 tap</b><span>to correct: a top-3 guess, or one dragged box</span></div>
    </div>
    <small data-at="0.3">100 synthetic multi-food plates built from Food-101 test images.</small>`, secs);
};

SCENES.nutrition = async (secs) => {
  await card(`
    <h2 data-at="0">Portions, nutrition, glycaemic load</h2>
    <div class="row">
      <div class="tile" data-at="0.08"><b>247 · 66 · 7</b><span>classes mapped exactly · by nearest food · left to you</span></div>
      <div class="tile" data-at="0.35"><b>±15–50%</b><span>portion bands: your grams · plate area · typical serving</span></div>
      <div class="tile" data-at="0.6"><b>57 + 78</b><span>foods with a published GI + foods borrowing their staple's GI</span>${SRC("of 286 foods")}</div>
    </div>`, secs);
};

SCENES.glucose = async (secs) => {
  await card(`
    <h2 data-at="0">The glucose estimate</h2>
    <div class="eq" data-at="0.1">dG/dt = R<sub>a</sub>(t) − k·G − U<sub>ex</sub>(t)</div>
    <div class="row">
      <div class="tile" data-at="0.2"><b>R<sub>a</sub></b><span>meal glucose appearing: available carbs × GI, slowed by fat, fibre, protein</span></div>
      <div class="tile" data-at="0.35"><b>k</b><span>clearance, set by the person's condition</span></div>
      <div class="tile" data-at="0.45"><b>U<sub>ex</sub></b><span>extra uptake by working muscle (MET × weight × time)</span></div>
      <div class="tile" data-at="0.7"><b>3 meals</b><span>with readings: calibrates to you (median ratio)</span></div>
    </div>`, secs);
};

SCENES.grounding = async (secs) => {
  await card(`
    <h2 data-at="0">A grounded Meal Advisor</h2>
    <div class="arch">
      <div class="box" data-at="0.08"><b>Your data</b>meals, profile, food table</div><div class="arrow" data-at="0.1">→</div>
      <div class="box" data-at="0.12"><b>Rule engine</b>writes the answer</div><div class="arrow" data-at="0.2">→</div>
      <div class="box side" data-at="0.22"><b>Qwen 2.5 (local)</b>rewords it</div><div class="arrow" data-at="0.3">→</div>
      <div class="box" data-at="0.32"><b>Validator</b>numbers · foods · safety</div><div class="arrow" data-at="0.4">→</div>
      <div class="box" data-at="0.42"><b>Shown</b>or the rule answer</div>
    </div>
    <div class="row">
      <div class="tile" data-at="0.7"><b>38 / 38</b><span>test questions passed</span>${SRC("arithmetic, safety, injection")}</div>
      <div class="tile" data-at="0.75"><b>0%</b><span>unsupported claims</span></div>
    </div>`, secs);
};

SCENES.learning = async (secs) => {
  await card(`
    <h2 data-at="0">Learning safely</h2>
    <div class="pains">
      <div class="tile" data-at="0.08"><b>Memory</b><span>fingerprint + cosine similarity ≥ 0.70: recognised next time, no retraining</span></div>
      <div class="tile" data-at="0.4"><b>Consent + screening</b><span>shared only if switched on; checked for poisoning patterns; people review the rest</span></div>
      <div class="tile" data-at="0.65"><b>Model gate</b><span>within 0.2 points of the live model on a fixed test set, safety foods no worse, then shadow mode</span></div>
    </div>`, secs);
};

SCENES.quality = async (secs) => {
  await card(`
    <h2 data-at="0">Tested and deployable</h2>
    <div class="row">
      <div class="tile" data-at="0.15"><b>65</b><span>automated tests, real PostgreSQL</span></div>
      <div class="tile" data-at="0.35"><b>9 / 9</b><span>acceptance checks, sign-up to saved meal, also offline</span></div>
      <div class="tile" data-at="0.6"><b>Restart</b><span>account, meal and photo kept</span></div>
      <div class="tile" data-at="0.75"><b>1 command</b><span>docker compose up, on a CPU server</span></div>
    </div>`, secs);
};


// ---- The final presentation (narration-final.json): the presenter in a corner over the demo, the evaluation and the
// system design. Figures come from docs/report/charts, made from the evidence files.
const FIG = (f, at = 0.05, alt = "") => `<img data-at="${at}" src="${chart(f)}" alt="${alt}">`;
const figCard = async (title, figs, secs, cls = "big", note = "") => { await chapter(""); return card(
  `<h2 data-at="0">${title}</h2><div class="charts ${cls}">${figs}</div>${note ? `<small data-at="0.5">${note}</small>` : ""}`, secs); };

SCENES.correct = async (secs) => { await SCENES.review(secs); await SCENES.mark(secs); };
SCENES.tryit = async (secs) => { await SCENES.portion(secs); await SCENES.whatif(secs); };
SCENES.evalmethod = async (secs) => { await chapter(""); await figCard("Eight experiments: input → method → output", FIG("20_experiments_flow.png"), secs); };
SCENES.datatrain = async (secs) => figCard("Data and training", FIG("14_data_prep.png", 0.03) + FIG("11_training_curves.png", 0.55), secs, "two");
SCENES.recognition = async (secs) => figCard("Recognition on 45,800 test images",
  FIG("01_model_metrics.png", 0.03) + FIG("13_per_class_f1.png", 0.4) + FIG("12_calibration.png", 0.7), secs, "three");
SCENES.platetest = async (secs) => figCard("Several foods on a plate", FIG("16_multifood_evidence.png"), secs);
SCENES.textlang = async (secs) => figCard("Language model, rules and TF-IDF",
  FIG("21_tfidf_matching.png", 0.03), secs, "big", "Meal explanations are now checked by the same validator as the advisor (v0.13.13).");
SCENES.results = async (secs) => card(`
    <h2 data-at="0">Advisor, glucose model, quality</h2>
    <div class="row small">
      <div class="tile" data-at="0.05"><b>38 / 38</b><span>advisor test questions, no unsupported claims</span>${SRC("advisor_eval.json")}</div>
      <div class="tile" data-at="0.15"><b>12 ms</b><span>median advisor reply (rules)</span></div>
      <div class="tile" data-at="0.65"><b>65</b><span>automated tests, real PostgreSQL</span></div>
      <div class="tile" data-at="0.75"><b>9 / 9</b><span>acceptance checks, also offline</span></div>
    </div>
    <div class="charts"><img data-at="0.3" src="${chart("07_glucose_curves.png")}" alt=""></div>`, secs);
SCENES.architecture = async (secs) => figCard("System design", FIG("19_system_detail.png"), secs);
SCENES.stages = async (secs) => figCard("The ten-stage pipeline", FIG("10_pipeline.png"), secs);
SCENES.grounded = async (secs) => figCard("Grounded by design", FIG("17_advisor_flow.png"), secs);
SCENES.safelearn = async (secs) => figCard("Learning safely", FIG("18_learning_flow.png"), secs);
SCENES.limits = async (secs) => card(`
    <h2 data-at="0">Limits, and what comes next</h2>
    <div class="pains">
      <div class="tile" data-at="0.08"><b>Similar dishes</b><span>45 of 320 classes below 50% F1</span></div>
      <div class="tile" data-at="0.3"><b>Portions</b><span>±35–50% from a photo; error not yet measured</span></div>
      <div class="tile" data-at="0.55"><b>Nutrition data</b><span>to verify against an official source</span></div>
    </div>
    <p data-at="0.8">Next: a trial with real users.</p>`, secs);
SCENES.close = async (secs) => SCENES.outro(secs);

// The opening runs over title cards on the landing page, signed out.
await page.goto(`${BASE}/`);
await page.waitForLoadState("networkidle");
// SCENES_MODE=screen records only the app demo ("screen" lines); the "camera" lines are the presenter's own video,
// spliced in later (voice.py splice). The default records every scene, title cards included.
const MODE = process.env.SCENES_MODE ?? "all";
for (const s of narration) {
  if (!SCENES[s.id]) throw new Error(`No scene "${s.id}" in record.mjs`);
  if (MODE === "screen" && s.mode === "camera") continue;
  await scene(s.id, SCENES[s.id]);
}

const video = page.video();
await context.close();
await browser.close();
const path = await video.path();
renameSync(path, join(OUT, "demo.webm"));
writeFileSync(join(OUT, "scenes.json"), JSON.stringify({ base: BASE, theme: THEME, scenes: log }, null, 1));
console.log(`video: ${join(OUT, "demo.webm")}`);
for (const s of log) if (s.actual > s.planned + 0.5) console.log(`   ${s.id} ran ${s.actual.toFixed(1)}s (planned ${s.planned.toFixed(1)}s)`);
