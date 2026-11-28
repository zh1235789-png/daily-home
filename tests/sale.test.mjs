import { test } from 'node:test';
import assert from 'node:assert/strict';
import { loadApp } from './harness.mjs';

const app = loadApp({ today: '2026-11-28T09:00:00+09:00' });
const sales = { updated: '2026-11-28T05:00+09:00', items: [
  { id: 'x', name: 'なし<b>', status: 'none', price: '年29,000円', checked: '2026-11-28T05:00+09:00' },
  { id: 'g', name: 'Google AI Pro', status: 'sale', price: '年14,500円（通常29,000円）', until: '2026-12-02', note: '新規のみ',
    sources: [{ title: '公式', url: 'https://one.google.com/' }, { title: '悪', url: 'javascript:alert(1)' }] },
] };

test('セール中が上・件数・残り日数・エスケープ', () => {
  const h = app.saleSec(sales, '2026-11-28');
  assert.match(h, /セール情報 <span class="n">1<\/span>/);
  assert.ok(h.indexOf('Google AI Pro') < h.indexOf('なし&lt;b&gt;'));
  assert.match(h, /あと4日（12\/2まで）/);
  assert.ok(!h.includes('なし<b>'));
  assert.ok(!h.includes('javascript:'));
  assert.match(h, /class="amber"/);
});

test('セールなしだけなら件数0で強調しない', () => {
  const h = app.saleSec({ items: [sales.items[0]] }, '2026-11-28');
  assert.match(h, /<span class="n">0<\/span>/);
  assert.match(h, /セールなし/);
  assert.ok(!h.includes('class="amber"'));
});
