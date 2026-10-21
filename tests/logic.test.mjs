import { test } from 'node:test';
import assert from 'node:assert/strict';
import { loadApp, norm } from './harness.mjs';

const app = loadApp({ today: '2026-10-20T09:00:00+09:00' });
const T = '2026-10-20';
const ids = (arr) => norm(arr).map((x) => x.id);

const hub = {
  week: [
    { id: 'w-over', text: '〜10/11 電話', due: '2026-10-11', done: false },
    { id: 'w-plain', text: '記録する', due: null, done: false },
    { id: 'w-done', text: '済み', due: null, done: true },
  ],
  dated: [
    { id: 'd-past', text: 'NVDA', due: '2026-10-15', done: false },
    { id: 'd-today', text: 'Apple課金', due: T, done: false },
    { id: 'd-asap', text: '電話', due: null, asap: true, done: false },
    { id: 'd-soon', text: '帰省', due: '2026-10-27', done: false },
    { id: 'd-far', text: '箱根', due: '2026-11-14', done: false },
    { id: 'd-range', text: 'iDeCo', start: '2026-10-25', due: '2026-12-24', done: false },
    { id: 'd-ongoing', text: '受付期間', start: '2026-10-01', due: '2026-10-30', done: false },
    { id: 'd-struck', text: '対応不要', due: '2026-10-10', done: true },
    { id: 'd-none', text: '時期未定', due: null, done: false },
  ],
};

test('期限切れ・今日・今週・今後・未定に分かれる', () => {
  const c = app.classify(hub, T);
  assert.deepEqual(ids(c.overdue), ['w-over', 'd-past']);
  assert.deepEqual(ids(c.today), ['d-today']);
  assert.deepEqual(ids(c.week).sort(), ['d-asap', 'd-ongoing', 'd-range', 'd-soon', 'w-plain'].sort());
  assert.deepEqual(ids(c.later), ['d-far']);
  assert.deepEqual(ids(c.undated), ['d-none']);
});

test('取り消し線（done）の項目はどこにも出ない', () => {
  const c = app.classify(hub, T);
  const all = [].concat(c.overdue, c.today, c.week, c.later, c.undated).map((x) => x.id);
  assert.ok(!all.includes('w-done'));
  assert.ok(!all.includes('d-struck'));
});

test('7日後ちょうどは今週、8日後は今後', () => {
  const c = app.classify({ dated: [
    { id: 'a', text: 'a', due: '2026-10-27', done: false },
    { id: 'b', text: 'b', due: '2026-10-28', done: false },
  ] }, T);
  assert.deepEqual(ids(c.week), ['a']);
  assert.deepEqual(ids(c.later), ['b']);
});

test('相対表示', () => {
  assert.equal(app.relLabel('2026-10-15', T), '5日超過');
  assert.equal(app.relLabel(T, T), '今日');
  assert.equal(app.relLabel('2026-10-21', T), '明日');
  assert.equal(app.relLabel('2026-10-27', T), 'あと7日');
});

test('JSTの日付：UTCで前日の夜でも東京の日付になる', () => {
  assert.equal(app.todayISO(new Date('2026-10-19T16:30:00Z')), '2026-10-20');
  assert.equal(app.todayISO(new Date('2026-10-20T14:59:00Z')), '2026-10-20');
});

test('完了報告はチェック済み・未送信のタスクハブ項目だけ', () => {
  const data = { hub: { week: [{ id: 'x', text: '**岩井コスモ**の記録', done: false, children: [] }],
    dated: [{ id: 'y', text: 'NVDA', done: false }], big: [{ id: 'p', text: '親', done: false, children: [{ id: 'c', text: '子', done: false }] }], someday: [] } };
  const p = app.pendingReports(data, { x: T, y: T, c: T, 'mail:u': T }, { y: T });
  assert.deepEqual(ids(p), ['x', 'c']);
  assert.equal(app.reportText(p), '✅完了: 岩井コスモの記録\n✅完了: 子');
});

test('HTMLはエスケープされ、強調と打ち消しだけ残る', () => {
  assert.equal(app.inline('<b>x</b> **強** ~~消~~ [[ノート|表示]]'), '&lt;b&gt;x&lt;/b&gt; <b>強</b> <s>消</s> 表示');
});

test('更新ボタン：押す前の状態は無視し、押した後の段階を表示する', () => {
  const pressed = Date.parse('2026-10-21T08:00:00+09:00');
  const old = { refresh: { stage: 'done', message: '更新しました', at: '2026-10-21T07:00:00+09:00' } };
  assert.equal(app.refreshMessage(old, pressed, pressed + 30000).done, false);
  const mid = { refresh: { stage: 'tasks', message: 'メール取得中', at: '2026-10-21T08:01:00+09:00' } };
  assert.deepEqual(norm(app.refreshMessage(mid, pressed, pressed + 60000)), { text: '⏳ メール取得中', done: false, err: false });
  const fin = { refresh: { stage: 'done', message: '更新しました', at: '2026-10-21T08:03:00+09:00' } };
  assert.equal(app.refreshMessage(fin, pressed, pressed + 180000).done, true);
  const bad = { refresh: { stage: 'error', message: '未ログイン', at: '2026-10-21T08:01:00+09:00' } };
  assert.equal(app.refreshMessage(bad, pressed, pressed + 60000).err, true);
});

test('更新ボタン：Macが7分応答しなければ打ち切る', () => {
  const pressed = Date.parse('2026-10-21T08:00:00+09:00');
  const m = app.refreshMessage({ refresh: null }, pressed, pressed + 8 * 60000);
  assert.equal(m.done, true);
  assert.equal(m.err, true);
});
