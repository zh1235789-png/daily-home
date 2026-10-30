import { test } from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { existsSync, mkdtempSync, writeFileSync } from 'node:fs';
import { tmpdir, homedir } from 'node:os';
import { join } from 'node:path';
import { loadApp, norm } from './harness.mjs';

const app = loadApp({ today: '2026-10-28T09:00:00+09:00' });
const training = {
  plan: [
    { days: [2], key: 'tue', label: '火', focus: '胸＋三頭', run: '朝ラン', leg: 'B', note: '' },
    { days: [3], key: 'wed', label: '水', focus: '背中＋二頭', run: 'ロング走（朝）', leg: null, kb: 'しっかり（スイング中心）', note: '脚なし' },
    { days: [6], key: 'sat', label: '土', focus: '胸と背中', run: 'なし（朝から仕事）', leg: 'C', note: '' },
  ],
  menus: { '1': { wed: { must: ['フロントプル', 'シュラッグ'], optional: ['ハンマーカール'] } }, '2': {} },
};

test('曜日で枠を選ぶ（2026-10-28は水曜）', () => {
  assert.equal(norm(app.trainingFor(training, '2026-10-28')).key, 'wed');
  assert.equal(norm(app.trainingFor(training, '2026-10-27')).key, 'tue');
});

test('枠の無い曜日（月・木）は休み', () => {
  assert.equal(app.trainingFor(training, '2026-10-29'), null);
  assert.equal(app.trainingFor(training, '2026-10-26'), null);
  assert.equal(app.trainingFor(null, '2026-10-28'), null);
});

test('今日の種目とランが出る・休みの日は散歩', () => {
  const h = app.trainSec(training, '2026-10-28');
  assert.match(h, /ロング走/);
  assert.match(h, /フロントプル/);
  assert.match(h, /脚なし/);
  assert.match(h, /明日（木）: 休み/);
  assert.match(h, /🔔 自宅ケトルベル: しっかり（スイング中心）（ランの日はランの後）/);
  assert.doesNotMatch(app.trainSec(training, '2026-10-31'), /自宅ケトルベル/);   // kb の無い枠には出さない
  assert.match(app.trainSec(training, '2026-10-29'), /今日は休み/);
});

test('ランが「なし」の日はランのチェックを出さない', () => {
  const h = app.trainSec(training, '2026-10-31');
  assert.doesNotMatch(h, /train:2026-10-31:run/);
  assert.match(h, /train:2026-10-31:gym/);
});

test('ラン・筋トレのチェックはタスクハブへ送らない', () => {
  const ids = app.hubIds({ hub: { week: [{ id: 'abc', children: [] }] }, training });
  assert.ok(!ids.has('train:2026-10-28:run'));
  assert.equal(app.doneBody(['train:2026-10-28:run']), '');
});

test('抽出スクリプト：WEEK_PLAN と DAY_MENUS を読める', () => {
  const dir = mkdtempSync(join(tmpdir(), 'dh-'));
  const f = join(dir, 'index.html');
  writeFileSync(f, `<script>
const DAY_MENUS = {
  '1': { wed: { must: ['a'], optional: [] } },
};
const WEEK_PLAN = [
  { days:[3], key:'wed', label:'水', focus:'背中', run:'ロング走', leg:null, note:'' },
];
</script>`);
  const out = JSON.parse(execFileSync('node', [new URL('../build/extract_training.mjs', import.meta.url).pathname, f], { encoding: 'utf8' }));
  assert.equal(out.plan[0].key, 'wed');
  assert.deepEqual(out.menus['1'].wed.must, ['a']);
});

test('抽出スクリプト：本物の筋トレAIコーチを読める（予定の中身は問わない）', { skip: !existsSync(join(homedir(), 'workout-ai-coach/index.html')) }, () => {
  const out = JSON.parse(execFileSync('node', [new URL('../build/extract_training.mjs', import.meta.url).pathname, join(homedir(), 'workout-ai-coach/index.html')], { encoding: 'utf8' }));
  assert.ok(out.plan.length > 0);
  out.plan.forEach((p) => { assert.ok(Array.isArray(p.days) && p.key && p.focus && typeof p.run === 'string'); });
  assert.ok(out.menus['1'] && out.menus['2']);
});
