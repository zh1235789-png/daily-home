import { test } from 'node:test';
import assert from 'node:assert/strict';
import { loadApp, norm } from './harness.mjs';

const app = loadApp({ today: '2026-10-28T09:00:00+09:00' });
const training = {
  plan: [
    { days: [3], key: 'wed', label: '水', focus: '背中＋二頭', run: 'ロング走（朝）', leg: null, note: '' },
    { days: [6], key: 'sat', label: '土', focus: '胸と背中', run: 'なし（朝から仕事）', leg: 'C', note: '' },
  ],
  menus: { '1': { wed: { must: ['フロントプル'], optional: [] } }, '2': {} },
};

test('今日のチェック項目: ランありはラン＋筋トレ、ランなしは筋トレだけ、休みは空', () => {
  assert.deepEqual(norm(app.trainIds(training, '2026-10-28')), ['train:2026-10-28:run', 'train:2026-10-28:gym']);
  assert.deepEqual(norm(app.trainIds(training, '2026-10-31')), ['train:2026-10-31:gym']);
  assert.deepEqual(norm(app.trainIds(training, '2026-10-29')), []);
  assert.deepEqual(norm(app.trainIds(null, '2026-10-28')), []);
});

test('健康タブのバッジは未チェックの数', () => {
  assert.equal(app.trainLeft({ training }, {}, '2026-10-28'), 2);
  assert.equal(app.trainLeft({ training }, { 'train:2026-10-28:run': '2026-10-28' }, '2026-10-28'), 1);
  assert.equal(app.trainLeft({}, {}, '2026-10-28'), 0);
});

test('日種別の目標カロリー: 両方1900・筋トレだけ1850・休み1650', () => {
  assert.equal(app.dayKind(training, '2026-10-28'), 'both');
  assert.equal(app.dayKind(training, '2026-10-31'), 'gym');
  assert.equal(app.dayKind(training, '2026-10-29'), 'rest');
  assert.match(app.foodSec(training, '2026-10-28'), /1,900 kcal/);
  assert.match(app.foodSec(training, '2026-10-29'), /1,650 kcal/);
});

test('健康タブ: 筋トレ・食事・週間の表・アプリ。予定が無くても落ちない', () => {
  const h = app.healthTab({ training }, '2026-10-28');
  assert.match(h, /🏃 ラン・筋トレ/);
  assert.match(h, /🍚 今日の食事の目標/);
  assert.equal((h.match(/<tr[ >]/g) || []).length, 8);   // 見出し＋月〜日
  assert.match(h, /📅 今週の運動/);
  assert.match(h, /healthtracker/);
  assert.match(app.healthTab({}, '2026-10-28'), /読み込めませんでした/);
});

test('保存したタブ health を読み戻す', () => {
  const a = loadApp({ today: '2026-10-28T09:00:00+09:00', storage: { 'dh.v1': JSON.stringify({ tab: 'health' }) } });
  assert.equal(a.loadState().tab, 'health');
});
