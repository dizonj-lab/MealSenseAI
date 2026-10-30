// Renders the video's title, statistic slide and closing cards at 1920x1080 from the proposal cover's own artwork.
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const here = __dirname;
const out = process.argv[2] || here;
const data = (f) => 'data:image/png;base64,' + fs.readFileSync(path.join(here, f)).toString('base64');
const cover = 'data:image/webp;base64,' + fs.readFileSync(path.join(here, 'cover.webp')).toString('base64');

const css = `
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@500;600;700;800&display=swap');
* { margin: 0; box-sizing: border-box; }
html, body { width: 1920px; height: 1080px; background: transparent; font-family: Montserrat, Arial, sans-serif; }
.ink { color: #0d2a2e; } .ai { color: #3cb895; }
.card { position: absolute; left: 150px; width: 1060px; background: rgba(13, 42, 46, .90); color: #fff;
  border-radius: 20px; padding: 30px 36px 26px; border-left: 8px solid #3cb895; box-shadow: 0 10px 40px rgba(0,0,0,.25); }
.card .big { font-size: 96px; font-weight: 800; line-height: 1; letter-spacing: -.01em; }
.card .big small { font-size: 52px; font-weight: 700; }
.card .what { font-size: 36px; font-weight: 600; line-height: 1.3; margin-top: 14px; }
.card .src { font-size: 21px; font-weight: 500; color: #9fd9c8; margin-top: 16px; line-height: 1.35; }
`;

const pages = {
  intro: `<body style="background:#f0f5f5">
    <img src="${cover}" style="position:absolute;left:-23px;top:0;width:1966px;height:1080px">
    <div style="position:absolute;left:120px;top:1043px;width:1095px;height:37px;background:#f0f5f5"></div>
    <div class="ink" style="position:absolute;left:146px;top:1045px;font-size:24px;font-weight:600;letter-spacing:.005em">
      Final Presentation <span class="ai" style="margin:0 22px">&bull;</span> Dizon Joselito Villanueva <span class="ai" style="margin:0 22px">&bull;</span> NUS-ISS</div>
  </body>`,
  'stat-diabetes': `<body><div class="card" style="top:215px">
    <div class="big">1 in 12</div>
    <div class="what">adults in Singapore live with diabetes (8.5%)</div>
    <div class="src">Ministry of Health, Singapore, 2023</div></div></body>`,
  'stat-cost': `<body><div class="card" style="top:575px">
    <div class="big">S$1.0B <small>&rarr;</small> S$2.5B</div>
    <div class="what">yearly cost of diabetes to Singapore, 2010 &rarr; 2050</div>
    <div class="src">Png et al., BMC Public Health, 2016</div></div></body>`,
  // The slide the statistics sit on; the presenter's take goes in its lower-right corner.
  'stats-bg': `<body style="background:#f0f5f5">
    <img src="${data('logo.png')}" style="position:absolute;left:70px;top:58px;height:106px">
    <img src="${data('skyline.png')}" style="position:absolute;left:150px;bottom:40px;width:620px;opacity:.55">
  </body>`,
  outro: `<body style="background:#f0f5f5">
    <img src="${data('logo.png')}" style="position:absolute;left:70px;top:58px;height:106px">
    <div style="position:absolute;left:0;right:0;top:300px;text-align:center">
      <div class="ink" style="font-size:132px;font-weight:800;letter-spacing:-.015em">MealSense<span class="ai">AI</span></div>
      <div style="width:150px;height:6px;background:#3cb895;border-radius:3px;margin:34px auto 38px"></div>
      <div class="ink" style="font-size:52px;font-weight:700">Understand your food. Make healthier choices.</div>
      <div class="ink" style="font-size:32px;font-weight:500;margin-top:26px;opacity:.8">Every plate a little clearer, one meal at a time.</div>
    </div>
    <img src="${data('skyline.png')}" style="position:absolute;left:50%;transform:translateX(-50%);bottom:110px;width:775px;opacity:.9">
    <div class="ink" style="position:absolute;left:0;right:0;bottom:48px;text-align:center;font-size:25px;font-weight:600">
      Thank you <span class="ai" style="margin:0 22px">&bull;</span> Dizon Joselito Villanueva <span class="ai" style="margin:0 22px">&bull;</span> NUS-ISS</div>
  </body>`,
};

(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1920, height: 1080 } });
  for (const [name, body] of Object.entries(pages)) {
    await p.setContent(`<!doctype html><html><head><meta charset="utf-8"><style>${css}</style></head>${body}</html>`);
    await p.evaluate(async () => { await Promise.all(['500','600','700','800'].map((w) => document.fonts.load(w + ' 40px Montserrat'))); await document.fonts.ready; });
    await p.waitForTimeout(300);
    await p.screenshot({ path: path.join(out, name + '.png'), omitBackground: !body.startsWith('<body style') });
    console.log(name, await p.evaluate(() => document.fonts.check('800 40px Montserrat')));
  }
  await b.close();
})();
