// Optional development check. Install: npm install --prefix .tmp-browser playwright-core
// Requires the app on port 8000 and Chrome or Edge installed locally.
const { chromium } = require('../.tmp-browser/node_modules/playwright-core');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const errors = [];
  const context = await browser.newContext({ viewport: { width: 1440, height: 1100 } });
  const page = await context.newPage();
  page.on('pageerror', error => errors.push(error.message));
  const base = process.env.BROWSER_BASE_URL || 'http://127.0.0.1:8000';
  const output = process.env.BROWSER_OUTPUT || path.join(__dirname, '..', 'reports', 'results');
  fs.mkdirSync(output, { recursive: true });
  async function actionAndResponse(action) {
    const [response] = await Promise.all([
      page.waitForResponse(r => new URL(r.url()).pathname === '/api/search'),
      action(),
    ]);
    const data = await response.json();
    await page.waitForFunction(() => document.querySelector('#results').getAttribute('aria-busy') === 'false');
    return { response, data };
  }
  try {
    await page.goto(base);
    await page.waitForFunction(() => document.querySelector('#collection-strip').textContent.includes('books to explore'));
    await page.screenshot({ path: path.join(output, 'desktop-home.png'), fullPage: true });
    await page.locator('#query').fill('whale');
    let result = await actionAndResponse(() => page.getByRole('button', { name: 'Explore books' }).click());
    assert.equal(result.response.status(), 200);
    assert.ok(result.data.total > 0);
    assert.deepEqual(await page.locator('.book-card h3').allTextContents(), result.data.results.map(b => b.title));
    assert.equal(await page.locator('.recommendation').count(), result.data.recommendations.length);
    if (result.data.total > result.data.page_size) {
      const firstPage = result.data.results.map(b => b.id);
      result = await actionAndResponse(() => page.locator('#next').click());
      assert.equal(result.data.page, 2);
      assert.ok(result.data.results.every(b => !firstPage.includes(b.id)));
      await actionAndResponse(() => page.locator('#previous').click());
    }
    result = await actionAndResponse(() => page.locator('#ranking').selectOption('frequency'));
    assert.ok(result.data.results.every((b, i, all) => i === 0 || all[i - 1].occurrences >= b.occurrences));
    await page.getByText('Advanced / Regex', { exact: true }).click();
    await page.locator('#query').fill('sea|ocean');
    result = await actionAndResponse(() => page.getByRole('button', { name: 'Explore books' }).click());
    assert.equal(result.response.status(), 200);
    assert.match(await page.locator('#matched-terms').innerText(), /ocean/);
    await page.locator('#query').fill('(');
    result = await actionAndResponse(() => page.getByRole('button', { name: 'Explore books' }).click());
    assert.equal(result.response.status(), 400);
    assert.match(await page.locator('#status').innerText(), /parenthesis/i);
    result = await actionAndResponse(() => page.locator('[data-query="adventure"]').click());
    assert.equal(result.response.status(), 200);
    await page.screenshot({ path: path.join(output, 'desktop-results.png'), fullPage: true });
    await page.setViewportSize({ width: 390, height: 844 });
    await page.screenshot({ path: path.join(output, 'mobile-results.png'), fullPage: true });
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);
    assert.equal(overflow, false, 'Mobile layout must not overflow horizontally.');
    await page.locator('#query').fill('frankenstein');
    result = await actionAndResponse(() => page.getByRole('button', { name: 'Explore books' }).click());
    assert.equal(result.response.status(), 200);
    assert.equal(await page.locator('.recommendation').count(), result.data.recommendations.length);
    const stats = await (await page.request.get(`${base}/api/stats`)).json();
    fs.writeFileSync(path.join(output, 'browser-check.json'), JSON.stringify({
      utc: new Date().toISOString(), books: stats.books, corpus_ready: stats.corpus_ready,
      checks: ['keyword', 'pagerank view', 'frequency ordering', 'pagination when available',
        'recommendations', 'regex', 'invalid regex', '390px mobile layout'],
      physical_multi_device_test: false, passed: true,
    }, null, 2));
    assert.deepEqual(errors, [], 'Browser JavaScript errors.');
    console.log('Browser checks passed: keyword, frequency ranking, recommendations, regex, invalid regex, mobile layout.');
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
