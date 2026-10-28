import { test } from 'node:test';
import assert from 'node:assert/strict';
import { loadApp, norm } from './harness.mjs';

const app = loadApp({ today: '2026-10-28T09:00:00+09:00' });
const data = { youtube: { items: [
  { id: 'a', date: '2026-10-27', title: 'ライブ<b>', url: 'https://www.youtube.com/watch?v=a', kind: 'live', minutes: 32,
    headline: '決算まとめ', points: ['コカコーラ好決算'], tickers: ['KO'], hanako: 'TSLAを買い増し' },
  { id: 'b', date: '2026-10-24', title: '古め', url: 'u', kind: 'video' },
  { id: 'c', date: '2026-10-10', title: '8日以上前', url: 'u' },
  { id: 'd', title: '日付なし', url: 'u' },
] } };

test('直近7日分だけ残す', () => {
  assert.deepEqual(norm(app.ytList(data, '2026-10-28')).map(v => v.id), ['a', 'b']);
  assert.deepEqual(norm(app.ytList({}, '2026-10-28')), []);
  assert.deepEqual(norm(app.ytList({ youtube: null }, '2026-10-28')), []);
});

test('昨日以降が新着、それより前は折りたたみ・HTMLはエスケープ', () => {
  const h = app.ytSec(app.ytList(data, '2026-10-28'), '2026-10-28');
  assert.match(h, /新着）? <span class="n">1<\/span>/);
  assert.match(h, /昨日 · ライブ · 32分/);
  assert.match(h, /それより前（1本）/);
  assert.match(h, /TSLAを買い増し/);
  assert.ok(!h.includes('ライブ<b>'));
});

test('新着が無い日は空表示', () => {
  const h = app.ytSec(norm(app.ytList(data, '2026-10-28')).slice(1), '2026-10-28');
  assert.match(h, /昨日・今日の新着はありません/);
});

test('YouTube以外のURLはリンクにしない', () => {
  const h = app.ytItem({ id: 'x', date: '2026-10-28', title: 'T', url: 'javascript:alert(1)' }, '2026-10-28');
  assert.ok(!h.includes('href'));
  assert.match(app.ytItem({ id: 'y', date: '2026-10-28', title: 'T', url: 'https://www.youtube.com/watch?v=y' }, '2026-10-28'), /href=/);
});
