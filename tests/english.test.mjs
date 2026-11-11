import { test } from 'node:test';
import assert from 'node:assert/strict';
import { loadApp } from './harness.mjs';

const app = loadApp({ today: '2026-10-28T09:00:00+09:00' });
const oet = { date: '2026-10-28', total: '約60分', lead: [], menu: [{ id: 'oet:a', prio: '🔴1', skill: 'L', text: '再解答', time: '30分' }, { id: 'oet:b', prio: '🟠2', skill: 'R', text: 'Part C', time: '22分' }] };

test('英語ルーティン: 曜日に関係なく毎日5つ、OETアプリはリンク付き', () => {
  for (const day of ['2026-10-28', '2026-10-29', '2026-10-31', '2026-11-01']) assert.equal(app.engRoutine(day).length, 5);
  const rt = app.engRoutine('2026-10-28');
  assert.ok(rt.every(r => r.id.startsWith('eng:2026-10-28:')));
  assert.equal(rt.map(r => r.name).join('|'), ['Abceed 瞬間英作文', 'Langaku', 'OET Reading', 'OET Speaking', 'OET Listening'].join('|'));
  assert.equal(rt.find(r => r.name === 'OET Reading').url, 'https://zh1235789-png.github.io/oet-reading-commute/');
  assert.equal(rt.find(r => r.name === 'Langaku').url, '');
  assert.equal(rt[0].note, '通勤の行き');
  assert.equal(rt[1].note, '通勤の帰り');
});

test('英語タブのバッジ: 今日のOETとルーティンの未チェック数。古いOETノートは数えない', () => {
  assert.equal(app.engLeft({ oet }, {}, '2026-10-28'), 7);
  assert.equal(app.engLeft({ oet }, { 'oet:a': '2026-10-28', 'eng:2026-10-28:reading': '2026-10-28' }, '2026-10-28'), 5);
  assert.equal(app.engLeft({ oet: Object.assign({}, oet, { date: '2026-10-27' }) }, {}, '2026-10-28'), 5);
  assert.equal(app.engLeft({}, {}, '2026-10-28'), 5);
});

test('英語タブ: OET・ルーティン・アプリを表示、OETノートが無くても落ちない', () => {
  const h = app.engTab({ oet }, '2026-10-28');
  assert.match(h, /🎧 OET/);
  assert.match(h, /Abceed 瞬間英作文/);
  assert.match(h, /href="https:\/\/zh1235789-png.github.io\/oet-listening-commute\/"/);
  assert.doesNotMatch(h, /DUO|Speak（/);
  assert.match(h, /oet-reading-commute/);
  assert.match(app.engTab({}, '2026-10-28'), /今日のOETノートがまだありません/);
});

test('タブバーに英語タブ・保存したタブ eng を読み戻す', () => {
  assert.match(app.tabNav('eng', {}, '2026-10-28'), /class="tb sel" data-act="tab" data-tab="eng"/);
  const a = loadApp({ today: '2026-10-28T09:00:00+09:00', storage: { 'dh.v1': JSON.stringify({ tab: 'eng' }) } });
  assert.equal(a.loadState().tab, 'eng');
});
