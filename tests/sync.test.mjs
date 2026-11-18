import { test } from 'node:test';
import assert from 'node:assert/strict';
import { loadApp, norm } from './harness.mjs';

const app = loadApp({ today: '2026-11-18T09:00:00+09:00' });
const data = { hub: { week: [{ id: 'aaaaaaaaaa', text: 't', children: [{ id: 'bbbbbbbbbb', text: 'c' }] }] } };

test('同期の対象: 英語・ラン筋トレ・抱負・OET（10桁）。タスクハブとメールは対象外', () => {
  assert.ok(app.syncable('eng:2026-11-18:langaku', data));
  assert.ok(app.syncable('train:2026-11-18:run', data));
  assert.ok(app.syncable('goal:0123456789', data));
  assert.ok(app.syncable('0123456789', data)); // OET メニュー
  assert.ok(!app.syncable('aaaaaaaaaa', data));
  assert.ok(!app.syncable('bbbbbbbbbb', data));
  assert.ok(!app.syncable('mail:https://mail.google.com/x', data));
  assert.ok(!app.syncable('eng:2026-11-18:Lang aku', data));
});

test('送る本文: まだ送っていない（0）ものだけ、今の状態を 0/1 で', () => {
  const body = app.syncBody({ 'eng:2026-11-18:langaku': 0, 'train:2026-11-18:run': 0, '0123456789': 61, 'bad id': 0 },
    { 'eng:2026-11-18:langaku': '2026-11-18', '0123456789': '2026-11-18' });
  assert.equal(body, 'k:eng:2026-11-18:langaku=1\nk:train:2026-11-18:run=0');
  assert.equal(app.syncBody({}, {}), '');
});

test('取り込み: 他の端末の新しい変更は採る。未送信・配布待ちのこの端末の変更は残す', () => {
  const st = { checks: { 'train:2026-11-18:run': '2026-11-18', 'eng:2026-11-18:reading': '2026-11-18', 'goal:0123456789': '2026-11-17' },
    sync: { 'train:2026-11-18:run': 60, 'eng:2026-11-18:reading': 0, 'goal:0123456789': 70 } };
  const changed = app.mergeSync(st, {
    'train:2026-11-18:run': [0, 62], // 他の端末が外した（新しい）→ 外す
    'eng:2026-11-18:reading': [0, 80], // この端末が未送信 → 残す
    'goal:0123456789': [0, 65], // この端末の 70 がまだ配られていない → 残す
    'eng:2026-11-18:langaku': [1, 63], // 他の端末で付けた → 付ける
    'bad id': [1, 99],
  }, '2026-11-18');
  assert.equal(changed, true);
  assert.deepEqual(norm(st.checks), { 'eng:2026-11-18:reading': '2026-11-18', 'goal:0123456789': '2026-11-17', 'eng:2026-11-18:langaku': '2026-11-18' });
  assert.deepEqual(norm(st.sync), { 'train:2026-11-18:run': 62, 'eng:2026-11-18:reading': 0, 'goal:0123456789': 70, 'eng:2026-11-18:langaku': 63 });
  // 同じものをもう一度取り込んでも変わらない。データに sync が無くても落ちない
  assert.equal(app.mergeSync(st, { 'eng:2026-11-18:langaku': [1, 63] }, '2026-11-18'), false);
  assert.equal(app.mergeSync(st, undefined, '2026-11-18'), false);
});

test('保存: 古い保存データ（sync 無し）・壊れた sync でも起動できる', () => {
  const a = loadApp({ today: '2026-11-18T09:00:00+09:00', storage: { 'dh.v1': JSON.stringify({ checks: { x: '2026-11-18' } }) } });
  assert.deepEqual(norm(a.loadState().sync), {});
  const b = loadApp({ today: '2026-11-18T09:00:00+09:00', storage: { 'dh.v1': JSON.stringify({ sync: 'x' }) } });
  assert.deepEqual(norm(b.loadState().sync), {});
});
