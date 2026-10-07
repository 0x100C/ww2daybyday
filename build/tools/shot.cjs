// Headless screenshots: node build/tools/shot.cjs out.png "?date=1939-09-12" [w h]
const { chromium } = require('playwright');
(async () => {
  const [out, query = '', w = '1280', h = '720'] = process.argv.slice(2);
  const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const page = await browser.newPage({ viewport: { width: +w, height: +h }, deviceScaleFactor: 1 });
  page.on('console', (m) => { if (m.type() === 'error' || m.type() === 'warning') console.log('console:', m.text()); });
  page.on('pageerror', (e) => console.log('pageerror:', e.message));
  await page.goto('http://127.0.0.1:3847/' + query);
  await page.waitForFunction(() => window.__app && window.__app.win !== null && window.__app.win !== undefined, null, { timeout: 120000 });
  await page.waitForTimeout(+(process.env.WAIT || 2500));
  await page.evaluate(() => { document.getElementById('bar').style.display = process_hide(); function process_hide(){ return location.search.includes('bar=1') ? '' : 'none'; } });
  await page.screenshot({ path: out });
  await browser.close();
})();
