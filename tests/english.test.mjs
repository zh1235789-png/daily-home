import { test } from 'node:test';
import assert from 'node:assert/strict';
import { loadApp } from './harness.mjs';

const app = loadApp({ today: '2026-10-28T09:00:00+09:00' });
const oet = { date: '2026-10-28', total: '約60分', lead: [], menu: [{ id: 'oet:a', prio: '🔴1', skill: 'L', text: '再解答', time: '30分' }, { id: 'oet:b', prio: '🟠2', skill: 'R', text: 'Part C', time: '22分' }] };

test('英語ルーティン: 曜日に関係なく毎日5つ、リンクは付けない', () => {
  for (const day of ['2026-10-28', '2026-10-29', '2026-10-31', '2026-11-01']) assert.equal(app.engRoutine(day).length, 5);
  const rt = app.engRoutine('2026-10-28');
  assert.ok(rt.every(r => r.id.startsWith('eng:2026-10-28:')));
  assert.equal(rt.map(r => r.name).join('|'), ['Abceed 瞬間英作文', 'Langaku', 'OET Reading', 'OET Speaking', 'OET Listening'].join('|'));
  assert.ok(rt.every(r => !('url' in r)));
  assert.equal(rt[3].note, '今日の5フレーズ');
  assert.equal(rt[0].note, '通勤の行き');
  assert.equal(rt[1].note, '通勤の帰り');
});

test('英語タブのバッジ: 今日のOETとルーティンの未チェック数。古いOETノートは数えない', () => {
  assert.equal(app.engLeft({ oet }, {}, '2026-10-28'), 7);
  assert.equal(app.engLeft({ oet }, { 'oet:a': '2026-10-28', 'eng:2026-10-28:reading': '2026-10-28' }, '2026-10-28'), 5);
  assert.equal(app.engLeft({ oet: Object.assign({}, oet, { date: '2026-10-27' }) }, {}, '2026-10-28'), 5);
  assert.equal(app.engLeft({}, {}, '2026-10-28'), 5);
});

test('英語タブ: OET・ルーティンを表示（アプリへのリンクは無し）、OETノートが無くても落ちない', () => {
  const h = app.engTab({ oet }, '2026-10-28');
  assert.match(h, /🎧 OET/);
  assert.match(h, /Abceed 瞬間英作文/);
  assert.doesNotMatch(h, /DUO|Speak（|github\.io|英語のアプリ/);
  assert.match(app.engTab({}, '2026-10-28'), /今日のOETノートがまだありません/);
});

test('タブバーに英語タブ・保存したタブ eng を読み戻す', () => {
  assert.match(app.tabNav('eng', {}, '2026-10-28'), /class="tb sel" data-act="tab" data-tab="eng"/);
  const a = loadApp({ today: '2026-10-28T09:00:00+09:00', storage: { 'dh.v1': JSON.stringify({ tab: 'eng' }) } });
  assert.equal(a.loadState().tab, 'eng');
});

// 2026-11-18：OETメニューのS行（今日の5フレーズ）と毎日の英語の OET Speaking が重なっていた
// → 毎日の英語を上に置き、Speaking アプリは毎日の英語に残して OET 側の行を出さない
const speakOet = { date: '2026-11-18', total: '約65分', lead: [], menu: [
  { id: 'oet:l', prio: '🔴1', skill: 'L', text: '再解答', time: '30分' },
  { id: 'oet:s', prio: '🟡3', skill: 'S', text: '**今日の5フレーズ**を全部✓ → アプリで10分', time: '10分' },
] };

test('英語タブは 毎日の英語 → OET → 目標 の順', () => {
  const h = app.engTab({ oet: speakOet }, '2026-11-18');
  const a = h.indexOf('📚 毎日の英語'), b = h.indexOf('🎧 OET'), c = h.indexOf('🎯 OET 目標');
  assert.ok(a >= 0 && a < b && b < c);
  assert.ok(app.engTab({}, '2026-11-18').indexOf('📚 毎日の英語') < app.engTab({}, '2026-11-18').indexOf('今日のOETノートがまだありません'));
});

test('OETメニューの5フレーズ／アプリのS行は出さず、毎日の英語の OET Speaking は毎日出す', () => {
  const h = app.engTab({ oet: speakOet }, '2026-11-18');
  assert.doesNotMatch(h, /data-id="oet:s"/);
  assert.match(h, /data-id="oet:l"/);
  assert.match(h, /data-id="eng:2026-11-18:speaking"/);
  assert.equal((h.match(/今日の5フレーズ/g) || []).length, 1);
  assert.match(h, /済 0\/5/);
  assert.equal(app.engRoutine('2026-11-18').length, 5);
  // バッジ：OET 1（S行は数えない）＋ ルーティン 5
  assert.equal(app.engLeft({ oet: speakOet }, {}, '2026-11-18'), 6);
  // 古い日付のノートでも S行は出さない
  assert.doesNotMatch(app.engTab({ oet: speakOet }, '2026-11-19'), /data-id="oet:s"/);
});

test('ロールプレイ録音など別のS行は OET に残す', () => {
  const rp = { ...speakOet, menu: [{ id: 'oet:r', prio: '🟡3', skill: 'S', text: 'ロールプレイ録音 ×1（Card14）', time: '15分' }] };
  assert.match(app.engTab({ oet: rp }, '2026-11-18'), /data-id="oet:r"/);
  assert.equal(app.engLeft({ oet: rp }, {}, '2026-11-18'), 6);
});
