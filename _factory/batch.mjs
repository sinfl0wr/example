// node batch.mjs outdir slug1 slug2 ...  -> errors/overflow per slug at 1440 and 390, full-page shots
import { chromium } from '/home/claude/.npm-global/lib/node_modules/@playwright/cli/node_modules/playwright-core/index.mjs';
const [,, outdir, ...slugs] = process.argv;
const b = await chromium.launch({ executablePath:'/opt/pw-browsers/chromium', chromiumSandbox:false });
for (const slug of slugs) {
  for (const w of [1440, 390]) {
    const p = await b.newPage({ viewport:{ width:w, height: w > 500 ? 900 : 844 } });
    const errs=[]; p.on('pageerror', e => errs.push(e.message)); p.on('console', m => { if (m.type()==='error') errs.push(m.text()); });
    p.on('requestfailed', r => errs.push('failed ' + r.url().slice(0, 80)));
    await p.goto(`http://localhost:8765/${slug}/`, { waitUntil:'networkidle' });
    await p.evaluate(() => document.querySelectorAll('img[loading=lazy]').forEach(i => i.loading = 'eager'));
    await p.evaluate(async () => { for (let y = 0; y < document.body.scrollHeight; y += 600) { scrollTo(0, y); await new Promise(r => setTimeout(r, 40)); } scrollTo(0,0); });
    await p.evaluate(() => document.querySelectorAll('.rv,.shutter,.flow').forEach(e => e.classList.add('in')));
    await p.waitForTimeout(900);
    const m = await p.evaluate(() => {
      const over = document.documentElement.scrollWidth - innerWidth;
      const wide = [...document.querySelectorAll('body *')].filter(e => { const r = e.getBoundingClientRect(); return r.width && r.right > innerWidth + 1 && getComputedStyle(e).position !== 'fixed'; }).slice(0, 3).map(e => e.tagName + '.' + e.className);
      const h1 = document.querySelector('h1'); const lh = h1 ? parseFloat(getComputedStyle(h1).lineHeight) : 0;
      const h1lines = h1 && lh ? Math.round(h1.getBoundingClientRect().height / lh) : 0;
      const broken = [...document.images].filter(i => i.offsetParent && i.complete && !i.naturalWidth).map(i => (i.getAttribute('src')||'EMPTY:'+(i.id||i.className||i.parentElement.className)) .slice(-40));
      return { over, wide, h1lines, broken, height: document.body.scrollHeight };
    });
    if (w === 1440 || slugs.length <= 3) await p.screenshot({ path: `${outdir}/${slug}-${w}.jpg`, fullPage: true, type: 'jpeg', quality: 50 });
    const bad = errs.length || m.over > 0 || m.broken.length;
    console.log(`${bad ? 'BAD ' : 'ok  '}${slug} @${w} h1:${m.h1lines} lines, height ${m.height}` + (bad ? ` over:${m.over} ${m.wide.join(' ')} broken:${m.broken.join(',')} errs(${errs.length}):${JSON.stringify(errs).slice(0, 400)}` : ''));
    await p.close();
  }
}
await b.close();
