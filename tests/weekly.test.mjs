// 週の点数（推移）と今週の抱負の表示。日曜の振り返りがデイリーノート・週の点数ノートに書いたものを出す。
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { loadApp } from './harness.mjs';

const app = loadApp({ today: '2026-11-15T21:00:00+09:00' });
const goals = {
  note: '2026-11-15', start: '2026-11-16', end: '2026-11-22', label: '11/16〜11/22',
  items: [
    { id: 'goal:a', text: '🇬🇧 **OET を4日以上**', done: false, why: '今週は1/7日', first: '朝に①' },
    { id: 'goal:b', text: '🏋️ 筋トレ3回', done: true, why: '', first: '' },
  ],
};

test('抱負は期間が終わるまで出し、終わったら出さない', () => {
  assert.ok(app.goalList({ goals }, '2026-11-15'));
  assert.ok(app.goalList({ goals }, '2026-11-22'));
  assert.equal(app.goalList({ goals }, '2026-11-23'), null);
  assert.equal(app.goalList({}, '2026-11-15'), null);
  assert.equal(app.goalList({ goals: { ...goals, items: [] } }, '2026-11-15'), null);
});

test('始まる前は「来週の抱負」、期間中は「今週の抱負」。残り数はノートの✓と端末のチェックを引く', () => {
  const before = app.goalSec(goals, '2026-11-15', {});
  assert.match(before, /来週の抱負（11\/16〜11\/22）/);
  assert.match(before, /<span class="n">1<\/span>/);
  assert.match(before, /<b>OET を4日以上<\/b>/);
  assert.match(before, /👣 朝に①/);
  const during = app.goalSec(goals, '2026-11-18', { 'goal:a': '2026-11-18' });
  assert.match(during, /今週の抱負/);
  assert.match(during, /<span class="n">0<\/span>/);
});

test('抱負のチェックはタスクハブやInboxへ送る対象に入らない', () => {
  const data = { hub: { week: [], dated: [], big: [], someday: [] }, goals };
  assert.equal(app.pendingReports(data, { 'goal:a': '2026-11-16' }, {}).length, 0);
  assert.equal(app.hubIds(data).has('goal:a'), false);
});

test('週の点数は最新の点数・前週差・内訳と、週ごとの棒を出す', () => {
  const list = [
    { week: '2026-11-08', label: '11/2〜11/8', total: 10, move: 10, eng: 0, gym: '1/4', cardio: '0/4', kb: '2/6', oet: '0/6', goals: '' },
    { week: '2026-11-15', label: '11/9〜11/15', total: 48, move: 40, eng: 8, gym: '3/4', cardio: '4/4', kb: '4/6', oet: '1/6', goals: '2.5/4' },
  ];
  const h = app.scoreSec(list);
  assert.match(h, /48<small>点<\/small>/);
  assert.match(h, /前週\+38/);
  assert.match(h, /運動 40\/50（筋トレ3\/4・有酸素4\/4・KB4\/6）/);
  assert.match(h, /抱負 2\.5\/4/);
  assert.equal((h.match(/class="sc-col"/g) || []).length, 2);
  assert.match(h, /class="move" style="height:40%"/);
});

test('週の点数が1週だけなら前週差は出さない', () => {
  const h = app.scoreSec([{ label: '11/9〜11/15', total: 48, move: 40, eng: 8, gym: '', cardio: '', kb: '', oet: '', goals: '' }]);
  assert.doesNotMatch(h, /前週/);
});

test('毎日の英語のチェックは「e:日付:5桁」でMacへ送る（ENG_DAILYの順・済=1）', () => {
  const checks = { 'eng:2026-11-16:shunkan': '2026-11-16', 'eng:2026-11-16:speaking': '2026-11-16', 'eng:2026-11-17:listening': '2026-11-17' };
  assert.equal(app.engMask(checks, '2026-11-16'), '10010');
  assert.equal(app.engMask(checks, '2026-11-18'), '00000');
  assert.equal(app.engBody({ '2026-11-17': '00001', '2026-11-16': '10010', bad: '1', '2026-11-18': '12' }), 'e:20261116:10010\ne:20261117:00001');
  assert.equal(app.engBody({}), '');
});

test('週の点数に毎日の英語の数を出す（記録が無い週は出さない）', () => {
  const base = { label: '11/16〜11/22', total: 70, move: 44, eng: 26, gym: '3/4', cardio: '4/4', kb: '4/4', oet: '4/6', goals: '' };
  assert.match(app.scoreSec([{ ...base, daily: '18/30' }]), /OET 4\/6日・毎日の英語 18\/30/);
  assert.doesNotMatch(app.scoreSec([{ ...base, daily: '' }]), /毎日の英語/);
});
