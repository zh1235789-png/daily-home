import { test } from 'node:test';
import assert from 'node:assert/strict';
import { loadApp } from './harness.mjs';

const app = loadApp({ today: '2026-10-28T09:00:00+09:00' });
const oet = { date: '2026-10-28', total: '約60分', lead: [], menu: [{ id: 'oet:a', prio: '🔴1', skill: 'L', text: '再解答', time: '30分' }, { id: 'oet:b', prio: '🟠2', skill: 'R', text: 'Part C', time: '22分' }] };

test('英語ルーティン: 毎日4つ、月・木・土・日は Speak を足す', () => {
  assert.equal(app.engRoutine('2026-10-28').length, 4); // 水
  assert.equal(app.engRoutine('2026-10-29').length, 5); // 木
  assert.equal(app.engRoutine('2026-10-31').length, 5); // 土
  assert.equal(app.engRoutine('2026-10-30').length, 4); // 金
  assert.ok(app.engRoutine('2026-10-28').every(r => r.id.startsWith('eng:2026-10-28:')));
});

test('英語タブのバッジ: 今日のOETとルーティンの未チェック数。古いOETノートは数えない', () => {
  assert.equal(app.engLeft({ oet }, {}, '2026-10-28'), 6);
  assert.equal(app.engLeft({ oet }, { 'oet:a': '2026-10-28', 'eng:2026-10-28:duo': '2026-10-28' }, '2026-10-28'), 4);
  assert.equal(app.engLeft({ oet: Object.assign({}, oet, { date: '2026-10-27' }) }, {}, '2026-10-28'), 4);
  assert.equal(app.engLeft({}, {}, '2026-10-28'), 4);
});

test('英語タブ: OET・ルーティン・アプリを表示、OETノートが無くても落ちない', () => {
  const h = app.engTab({ oet }, '2026-10-28');
  assert.match(h, /🎧 OET/);
  assert.match(h, /DUO 例文英訳/);
  assert.match(h, /oet-reading-commute/);
  assert.match(app.engTab({}, '2026-10-28'), /今日のOETノートがまだありません/);
});

test('タブバーに英語タブ・保存したタブ eng を読み戻す', () => {
  assert.match(app.tabNav('eng', {}, '2026-10-28'), /class="tb sel" data-act="tab" data-tab="eng"/);
  const a = loadApp({ today: '2026-10-28T09:00:00+09:00', storage: { 'dh.v1': JSON.stringify({ tab: 'eng' }) } });
  assert.equal(a.loadState().tab, 'eng');
});
