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
    { days: [3], key: 'wed', label: '水', focus: '背中＋二頭', run: 'ロング走（朝）', leg: null, kb: 'しっかり（スイング中心）', kbShort: 'しっかり', kbLevel: 'heavy', kbUpper: true, note: '脚なし' },
    { days: [6], key: 'sat', label: '土', focus: '胸と背中', run: 'なし（朝から仕事）', leg: 'C', note: '' },
  ],
  menus: { '1': { wed: { must: ['フロントプル', 'シュラッグ'], optional: ['ハンマーカール'] } }, '2': {} },
  kbMenus: { heavy: { label: 'しっかり（水・日）', items: ['両手スイング'] }, upper: { label: '上半身（日曜）', items: ['ハンマーカール'] } },
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
  assert.match(h, /data-id="train:2026-10-28:kb"/);
  assert.match(h, /🔔 <b>自宅ケトルベル（しっかり）<\/b>/);
  assert.match(h, /しっかり（水・日）<\/div><ol><li>両手スイング<\/li><\/ol>.*上半身（日曜）<\/div><ol><li>ハンマーカール/);
  assert.doesNotMatch(app.trainSec(training, '2026-10-31'), /自宅ケトルベル/);   // kb の無い枠には出さない
  assert.match(app.trainSec(training, '2026-10-29'), /今日は休み/);
});

test('ランが「なし」の日はランのチェックを出さない', () => {
  const h = app.trainSec(training, '2026-10-31');
  assert.doesNotMatch(h, /train:2026-10-31:run/);
  assert.match(h, /train:2026-10-31:gym/);
});

test('ケトルベルのある日はチェック項目に入り、未完了の数に数える', () => {
  assert.deepEqual(norm(app.trainIds(training, '2026-10-28')), ['train:2026-10-28:run', 'train:2026-10-28:gym', 'train:2026-10-28:kb']);
  assert.deepEqual(norm(app.trainIds(training, '2026-10-31')), ['train:2026-10-31:gym']);
  assert.equal(app.trainLeft({ training }, { 'train:2026-10-28:kb': true }, '2026-10-28'), 2);
  assert.equal(app.doneBody(['train:2026-10-28:kb']), '');   // タスクハブへは送らない
});

test('ラン・筋トレのチェックはタスクハブへ送らない', () => {
  const ids = app.hubIds({ hub: { week: [{ id: 'abc', children: [] }] }, training });
  assert.ok(!ids.has('train:2026-10-28:run'));
  assert.equal(app.doneBody(['train:2026-10-28:run']), '');
});

test('今週の運動は月〜日の表（ラン・筋トレ・ケトルベル）で今日を強調し、KBメニューを出す', () => {
  const t = { ...training, plan: training.plan.map(p => p.key === 'wed' ? { ...p, runShort: 'ロング走', gymShort: '背中＋二頭', kbShort: 'しっかり' } : p),
    kbMenus: { light: { label: '軽め（火・金・土）', items: ['片脚RDL 左右3×8'] } } };
  const h = app.weekPlanSec(t, '2026-10-28');   // 水
  const days = [...h.matchAll(/<tr[^>]*><td>(.)<\/td>/g)].map(m => m[1]).join('');
  assert.equal(days, '月火水木金土日');
  assert.match(h, /<tr class="today"><td>水<\/td><td>ロング走<\/td><td>背中＋二頭<\/td><td>しっかり<\/td>/);
  assert.match(h, /<td>火<\/td><td>朝ラン<\/td><td>胸＋三頭<\/td><td><\/td>/);   // 短い名前が無い版はそのまま
  assert.equal((h.match(/オフ（手術日）/g) || []).length, 4);   // この fixture は火・水・土だけ（月・木・金・日が休み）
  assert.match(h, /軽め（火・金・土）<\/b><ul><li>片脚RDL 左右3×8/);
  assert.doesNotMatch(app.weekPlanSec({ ...training, kbMenus: undefined }, '2026-10-28'), /ケトルベルのメニュー/);   // 古いデータ（kbMenus無し）
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
  if (out.kbMenus) Object.values(out.kbMenus).forEach((m) => { assert.ok(m.label && Array.isArray(m.items)); });
});
