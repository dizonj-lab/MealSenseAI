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
.title { position: absolute; left: 150px; top: 178px; font-size: 46px; font-weight: 800; color: #0d2a2e; }
.tile { position: absolute; width: 375px; height: 215px; background: #fff; border-radius: 18px; border-top: 7px solid #3cb895;
  box-shadow: 0 8px 28px rgba(13,42,46,.12); padding: 24px 26px; color: #0d2a2e; }
.tile b { display: block; font-size: 33px; font-weight: 800; margin-bottom: 10px; }
.tile span { font-size: 21px; font-weight: 500; line-height: 1.35; color: #34545a; }
.limit { position: absolute; left: 150px; width: 860px; background: #fff; border-radius: 18px; border-left: 8px solid #e8833a;
  box-shadow: 0 8px 28px rgba(13,42,46,.12); padding: 22px 30px; color: #0d2a2e; }
.limit b { display: block; font-size: 33px; font-weight: 800; margin-bottom: 8px; }
.limit span { font-size: 22px; font-weight: 500; line-height: 1.4; color: #34545a; }
.next { position: absolute; left: 1070px; top: 270px; width: 700px; background: rgba(13,42,46,.94); color: #fff; border-radius: 20px;
  padding: 28px 34px 26px; border-left: 8px solid #3cb895; }
.next h3 { font-size: 34px; font-weight: 800; margin-bottom: 18px; }
.step { display: grid; grid-template-columns: 46px 1fr; gap: 14px; margin-top: 14px; }
.step i { width: 40px; height: 40px; border-radius: 50%; background: #3cb895; color: #0d2a2e; font: 800 22px Montserrat, Arial;
  display: grid; place-items: center; font-style: normal; }
.step b { display: block; font-size: 25px; font-weight: 700; }
.step span { font-size: 20px; font-weight: 500; color: #b8e6d8; line-height: 1.35; }
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
  'features-bg': `<body style="background:#f0f5f5">
    <img src="${data('logo.png')}" style="position:absolute;left:70px;top:58px;height:106px">
    <div class="title">What MealSenseAI measures</div>
  </body>`,
  'feat-1': `<body><div class="tile" style="left:150px;top:270px"><b>Foods</b><span>320 dishes; several foods on one plate</span></div></body>`,
  'feat-2': `<body><div class="tile" style="left:555px;top:270px"><b>Portions</b><span>grams, each with a range</span></div></body>`,
  'feat-3': `<body><div class="tile" style="left:960px;top:270px"><b>Nutrients</b><span>kcal, carbs, protein, fat, sat. fat, sugar, fibre, sodium</span></div></body>`,
  'feat-4': `<body><div class="tile" style="left:1365px;top:270px"><b>Blood-sugar effect</b><span>the likely glucose curve after the meal</span></div></body>`,
  'feat-5': `<body><div class="tile" style="left:150px;top:515px"><b>Glycaemic load</b><span>per food and for the whole meal</span></div></body>`,
  'feat-6': `<body><div class="tile" style="left:555px;top:515px"><b>Next step</b><span>a practical suggestion, such as a walk after eating</span></div></body>`,
  'feat-7': `<body><div class="tile" style="left:960px;top:515px"><b>Range & source</b><span>every estimate labelled with its type and range</span></div></body>`,
  'feat-8': `<body><div class="tile" style="left:1365px;top:515px"><b>You confirm</b><span>nothing is saved until you review it</span></div></body>`,
  'limits-bg': `<body style="background:#f0f5f5">
    <img src="${data('logo.png')}" style="position:absolute;left:70px;top:58px;height:106px">
    <div class="title">Limitations and next steps</div>
  </body>`,
  'limit-1': `<body><div class="limit" style="top:270px"><b>Similar dishes get confused</b><span>dumpling &harr; xiao long bao, steak &harr; filet mignon; weakest: mee siam, soto bee hoon, bee hoon</span></div></body>`,
  'limit-2': `<body><div class="limit" style="top:455px"><b>Portions: margin up to &plusmn;50%</b><span>estimated from one photo; not yet measured against weighed food</span></div></body>`,
  'limit-3': `<body><div class="limit" style="top:610px"><b>Nutrition values not yet verified</b><span>204 approximated foods, to be checked against an official source</span></div></body>`,
  'next-steps': `<body><div class="next"><h3>Next: a trial with real users</h3><div class="step"><i>1</i><div><b>Moderated sessions</b><span>5&ndash;8 users try the app with me</span></div></div><div class="step"><i>2</i><div><b>Two-week field trial</b><span>15&ndash;30 participants; weighed portions for portion error</span></div></div><div class="step"><i>3</i><div><b>Verified nutrition source</b><span>a Singapore food table replaces the approximations</span></div></div><div class="step"><i>4</i><div><b>Retrain the model</b><span>consented user photos, focused on the confused local dishes</span></div></div></div></body>`,
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
