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
  // 並びはラン → ケトルベル → 筋トレ
  assert.ok(h.indexOf(':run"') < h.indexOf(':kb"') && h.indexOf(':kb"') < h.indexOf(':gym"'));
  assert.match(h, /🔔 <b>自宅ケトルベル（しっかり）<\/b>/);
  assert.match(h, /しっかり（水・日）<\/div><ol><li>両手スイング<\/li><\/ol>.*上半身（日曜）<\/div><ol><li>ハンマーカール/);
  assert.doesNotMatch(app.trainSec(training, '2026-10-31'), /自宅ケトルベル/);   // kb の無い枠には出さない
  assert.match(app.trainSec(training, '2026-10-29'), /今日は休み/);
});

test('kbExtra（金・日の朝の腕タバタ）のメニューも並べる（2026-11-12）', () => {
  const t = { ...training,
    plan: training.plan.map(p => p.key === 'wed' ? { ...p, kbUpper: undefined, kbExtra: ['armtabata'] } : p),
    kbMenus: { ...training.kbMenus, armtabata: { label: '腕タバタ（金・日の朝）', items: ['ハンマーカール⇄フレンチプレス'] } } };
  const h = app.trainSec(t, '2026-10-28');
  assert.match(h, /しっかり（水・日）<\/div><ol><li>両手スイング<\/li><\/ol>.*腕タバタ（金・日の朝）<\/div><ol><li>ハンマーカール⇄フレンチプレス/);
  assert.doesNotMatch(h, /上半身（日曜）/);
});

test('ランが「なし」の日はランのチェックを出さない', () => {
  const h = app.trainSec(training, '2026-10-31');
  assert.doesNotMatch(h, /train:2026-10-31:run/);
  assert.match(h, /train:2026-10-31:gym/);
});

test('ケトルベルのある日はチェック項目に入り、未完了の数に数える', () => {
  assert.deepEqual(norm(app.trainIds(training, '2026-10-28')), ['train:2026-10-28:run', 'train:2026-10-28:kb', 'train:2026-10-28:gym']);
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

test('月・木（手術日）はコーチの OFF_DAY_PLAN から朝のウォーキングと体幹メニューを出す（2026-11-01）', () => {
  const t = {
    ...training,
    kbMenus: { ...training.kbMenus, core: { label: '体幹・瞬発（月・木の朝）', items: ['片手ハイプル 左右5×3', '体幹タバタ'] } },
    offDay: { days: [1, 4], key: 'off', run: '朝ウォーキング20〜30分', runShort: '朝ウォーキング', gymShort: 'オフ（手術日）', kbShort: '体幹・瞬発（朝）', kbLevel: 'core', kb: '体幹', note: 'ハムを休ませる' },
  };
  assert.equal(norm(app.offDayFor(t, '2026-10-29')).key, 'off');   // 木
  assert.equal(app.offDayFor(t, '2026-10-28'), null);              // 水（ジムの日）
  assert.equal(app.offDayFor(training, '2026-10-29'), null);       // offDay の無い古いデータ
  // 曜日ごとの上書き（2026-11-12〜。月は体幹タバタだけ）
  const t2 = { ...t, offDay: { ...t.offDay, byDay: { 1: { kbShort: '体幹タバタ（朝）', kbLevel: 'coretabata' }, 4: {} } } };
  assert.equal(app.offDayFor(t2, '2026-11-16').kbLevel, 'coretabata');   // 月
  assert.equal(app.offDayFor(t2, '2026-11-19').kbLevel, 'core');         // 木
  assert.equal(app.offDayFor(t2, '2026-11-16').run, '朝ウォーキング20〜30分');   // 上書きしない項目は元のまま
  const h = app.trainSec(t, '2026-10-29');
  assert.match(h, /今日はジムなし（手術日）/);
  assert.match(h, /🚶 朝ウォーキング20〜30分/);
  assert.match(h, /自宅ケトルベル（体幹・瞬発（朝））/);
  assert.match(h, /<li>片手ハイプル 左右5×3<\/li><li>体幹タバタ<\/li>/);
  assert.match(h, /data-id="train:2026-10-29:kb"/);
  assert.match(app.trainSec(t, '2026-10-28'), /明日（木）: ジムなし（手術日）・朝ウォーキング＋ケトルベル体幹/);
  const w = app.weekPlanSec(t, '2026-10-28');
  assert.match(w, /<td>月<\/td><td class="off">朝ウォーキング<\/td><td class="off">オフ（手術日）<\/td><td>体幹・瞬発（朝）<\/td>/);
});

test('チェックを保存する ID（trainIds）は、画面に出すチェック（trainSec）と曜日を問わず一致する（2026-11-12: 月・木のチェックが開くたびに消えた）', () => {
  const t = {
    ...training,
    kbMenus: { ...training.kbMenus, core: { label: '体幹・瞬発', items: ['体幹タバタ'] } },
    offDay: { days: [1, 4], key: 'off', run: '朝ウォーキング20〜30分', kbShort: '体幹・瞬発（朝）', kbLevel: 'core', kb: '体幹' },
  };
  assert.deepEqual(norm(app.trainIds(t, '2026-11-12')), ['train:2026-11-12:walk', 'train:2026-11-12:kb']);   // 木
  for (let i = 0; i < 7; i++) {
    const day = app.addDays('2026-11-09', i);
    const shown = [...app.trainSec(t, day).matchAll(/data-id="([^"]+)"/g)].map(m => m[1]).sort();
    assert.deepEqual(norm(app.trainIds(t, day)).slice().sort(), shown, day);
  }
  assert.equal(app.trainLeft({ training: t }, { 'train:2026-11-12:walk': '2026-11-12' }, '2026-11-12'), 1);
});

test('週末のバイク4×4: コーチの alt で、第2・4土曜の週は土曜、それ以外の週は日曜（2026-11-14）', () => {
  const t = { ...training, plan: [
    { days: [6], key: 'sat', label: '土', focus: '胸と背中', run: 'なし（第1・3・5土曜は朝から仕事）', runShort: 'なし', leg: null, note: '',
      alt: { satNth: [2, 4], runShort: 'バイク4×4', run: 'バイク4×4（第2・4土曜。筋トレ前）' } },
    { days: [0], key: 'sun', label: '日', focus: '振替', run: 'バイク4×4（筋トレ前）', runShort: 'バイク4×4', leg: null, note: '',
      alt: { satNth: [2, 4], runShort: 'なし（バイクは土曜）', run: 'なし（バイク4×4は土曜に済ませた週）' } },
  ] };
  assert.equal(app.satNthOfWeek('2026-11-14'), 2);
  assert.equal(app.satNthOfWeek('2026-11-15'), 2);   // 日曜は前日の土曜で決まる
  assert.equal(app.satNthOfWeek('2026-03-01'), 4);   // 前日は2/28（第4土曜）
  assert.equal(app.satNthOfWeek('2026-11-01'), 5);   // 前日は10/31（第5土曜）
  // 第2土曜の週: 土曜にバイクのチェック（Garminの注意は出さない）、日曜はランのチェックなし
  const sat = app.trainSec(t, '2026-11-14');
  assert.match(sat, /data-id="train:2026-11-14:run"/);
  assert.match(sat, /🚴 バイク4×4（第2・4土曜。筋トレ前）/);
  assert.match(sat, /筋トレAIコーチの「有酸素運動を記録 → バイク4×4」/);
  assert.doesNotMatch(sat, /Garminコーチ/);
  assert.deepEqual(norm(app.trainIds(t, '2026-11-15')), ['train:2026-11-15:gym']);
  assert.equal(app.dayKind(t, '2026-11-14'), 'both');
  assert.equal(app.dayKind(t, '2026-11-15'), 'gym');
  // 第3土曜の週: 今までどおり日曜
  assert.deepEqual(norm(app.trainIds(t, '2026-11-21')), ['train:2026-11-21:gym']);
  assert.match(app.trainSec(t, '2026-11-22'), /🚴 バイク4×4（筋トレ前）/);
  // 今週の表も週ごとに変わる
  assert.match(app.weekPlanSec(t, '2026-11-12'), /<td>土<\/td><td>バイク4×4<\/td>.*<td>日<\/td><td>なし（バイクは土曜）<\/td>/s);
  assert.match(app.weekPlanSec(t, '2026-11-19'), /<td>土<\/td><td>なし<\/td>.*<td>日<\/td><td>バイク4×4<\/td>/s);
  // alt の無い古いデータは今までどおり
  assert.equal(norm(app.trainingFor(training, '2026-11-14')).run, 'なし（朝から仕事）');
});

test('抽出スクリプト：コーチの alt（その週だけの上書き）もそのまま渡す', () => {
  const dir = mkdtempSync(join(tmpdir(), 'coach-'));
  const f = join(dir, 'index.html');
  writeFileSync(f, `<script>
const WEEK_PLAN = [
  { days:[6], key:'sat', label:'土', focus:'胸と背中', run:'なし', leg:null,
    alt:{ satNth:[2,4], runShort:'バイク4×4', run:'バイク4×4（第2・4土曜）' } },
];
const DAY_MENUS = {
  '1': {},
};
</script>`);
  const out = JSON.parse(execFileSync('node', [new URL('../build/extract_training.mjs', import.meta.url).pathname, f], { encoding: 'utf8' }));
  assert.deepEqual(out.plan[0].alt, { satNth: [2, 4], runShort: 'バイク4×4', run: 'バイク4×4（第2・4土曜）' });
});

test('バイク4×4の日はジムのチェックに腹筋を足す（コーチの abs、2026-11-14）', () => {
  const absMenu = { must: ['アブドミナル（志村マシン）', 'ロータリートルソー（志村マシン）'], optional: ['リバースクランチ（ベンチ）'], note: 'バイク4×4のあとに' };
  const t = { ...training,
    plan: [
      { days: [6], key: 'sat', label: '土', focus: '胸と背中', run: 'なし（朝から仕事）', leg: null, note: '',
        alt: { satNth: [2, 4], run: 'バイク4×4（第2・4土曜）', abs: true } },
      { days: [0], key: 'sun', label: '日', focus: '振替', run: 'バイク4×4', leg: null, note: '', abs: true,
        alt: { satNth: [2, 4], run: 'なし（バイク4×4は土曜に済ませた週）', abs: false } },
    ],
    menus: { '1': { sat: { must: ['マシンチェストプレス'], optional: [] }, abs: absMenu }, '2': {} } };
  const sat = app.trainSec(t, '2026-11-14');   // 第2土曜（バイク）
  assert.match(sat, /🏋️ <b>胸と背中＋腹筋<\/b>/);
  assert.match(sat, /マシンチェストプレス.*💪 腹筋（バイク4×4のあと）<\/div><ol><li>アブドミナル（志村マシン）<\/li><li>ロータリートルソー（志村マシン）<\/li><\/ol>.*リバースクランチ（ベンチ）.*※ バイク4×4のあとに/s);
  assert.match(app.trainSec(t, '2026-11-22'), /🏋️ <b>振替＋腹筋<\/b>/);   // 第3土曜の週の日曜（バイク）
  for (const ds of ['2026-11-15', '2026-11-21']) assert.doesNotMatch(app.trainSec(t, ds), /腹筋/, ds);   // バイクのない日曜・土曜
  // 腹筋のメニューが無い古いデータでは出さない
  assert.doesNotMatch(app.trainSec({ ...t, menus: { '1': {}, '2': {} } }, '2026-11-14'), /腹筋/);
});
