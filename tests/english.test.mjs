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
const speakOet = { date: '2026-11-18', total: '約65分', lead: [], menu: [
  { id: 'oet:l', prio: '🔴1', skill: 'L', text: '再解答', time: '30分' },
  { id: 'oet:s', prio: '🟡3', skill: 'S', text: '**今日の5フレーズ**を全部✓ → アプリで10分', time: '10分' },
] };

test('OETメニューに5フレーズのS行がある日は、毎日の英語から OET Speaking を外す', () => {
  assert.equal(app.oetSpeakId({ oet: speakOet }, '2026-11-18'), 'oet:s');
  const rt = app.engRoutine('2026-11-18', { oet: speakOet });
  assert.equal(rt.length, 4);
  assert.ok(!rt.some(r => r.id === 'eng:2026-11-18:speaking'));
  assert.equal(app.engRoutine('2026-11-18').length, 5, 'd なし（後片づけ用）は5つ全部');
  const h = app.engTab({ oet: speakOet }, '2026-11-18');
  assert.equal((h.match(/今日の5フレーズ/g) || []).length, 2, 'OETのS行と案内の1行だけ（チェック欄は1つ）');
  assert.doesNotMatch(h, /<b>OET Speaking<\/b>/);
  assert.match(h, /済 0\/4/);
  // バッジ：OET 2 ＋ ルーティン 4
  assert.equal(app.engLeft({ oet: speakOet }, {}, '2026-11-18'), 6);
});

test('ロールプレイ録音など別のS行の日・古いOETノートの日は、OET Speaking を残す', () => {
  const rp = { ...speakOet, menu: [{ id: 'oet:r', prio: '🟡3', skill: 'S', text: 'ロールプレイ録音 ×1（Card14）', time: '15分' }] };
  assert.equal(app.oetSpeakId({ oet: rp }, '2026-11-18'), '');
  assert.equal(app.engRoutine('2026-11-18', { oet: rp }).length, 5);
  assert.equal(app.engRoutine('2026-11-19', { oet: speakOet }).length, 5);
  assert.equal(app.engRoutine('2026-11-18', {}).length, 5);
});

test('Speaking の記録（週の点数用の5桁）は OET のS行のチェックでも 1 になる', () => {
  assert.equal(app.engMask({ 'oet:s': '2026-11-18' }, '2026-11-18', 'oet:s'), '00010');
  assert.equal(app.engMask({}, '2026-11-18', 'oet:s'), '00000');
  assert.equal(app.engMask({ 'oet:s': '2026-11-18' }, '2026-11-18', ''), '00000');
});
