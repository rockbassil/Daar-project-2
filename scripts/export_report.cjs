// Optional report export using the existing local Playwright/Chrome development tool.
const { chromium } = require('../.tmp-browser/node_modules/playwright-core');
const { pathToFileURL } = require('node:url');
const path = require('node:path');
const fs = require('node:fs');

(async () => {
  const root = path.join(__dirname, '..');
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  try {
    const page = await browser.newPage({ viewport: { width: 900, height: 1200 } });
    await page.goto(pathToFileURL(path.join(root, 'docs/report-draft.html')).href);
    await page.emulateMedia({ media: 'print' });
    await page.evaluate(() => document.fonts.ready);
    const broken = await page.locator('img').evaluateAll(images => images.filter(i => !i.complete || i.naturalWidth === 0).map(i => i.src));
    if (broken.length) throw new Error(`Missing report images: ${broken.join(', ')}`);
    await page.pdf({ path: path.join(root, 'docs/report-draft.pdf'), preferCSSPageSize: true, printBackground: true });
    const output = path.join(root, 'reports/audit-2026-10-20/report-preview');
    fs.mkdirSync(output, { recursive: true });
    for (const index of [0, 5, 9, 11]) {
      await page.locator('section.page').nth(index).screenshot({ path: path.join(output, `page-${index + 1}.png`) });
    }
    console.log('Exported docs/report-draft.pdf; review page count and the pending evidence before submission.');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
