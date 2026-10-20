// index.html が起動時に例外を出さないことの回帰テスト。
import { test } from 'node:test';
import { assertLoads } from './harness.mjs';

test('index.html が例外なく初期化できる', () => {
  assertLoads({ today: '2026-10-20T09:00:00+09:00' });
});

test('保存データが空でも初期化できる（初回起動）', () => {
  assertLoads({ today: '2026-10-20T09:00:00+09:00', storage: {} });
});

test('保存データが壊れていても初期化できる', () => {
  assertLoads({ today: '2026-10-20T09:00:00+09:00', storage: { 'dh.v1': 'not json{' } });
});
