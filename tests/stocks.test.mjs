import { test } from 'node:test';
import assert from 'node:assert/strict';
import { loadApp, norm } from './harness.mjs';

const app = loadApp({ today: '2026-10-28T09:00:00+09:00' });
const rules = [{ group: 'index', label: '指数連動', threshold: 10 }, { group: 'strong', label: '強い会社', threshold: 20 }, { group: 'other', label: 'Hanako30', threshold: 30 }];
const stocks = { asof: '2026-10-28', watching: 81, failed: [], rules, alerts: [
  { ticker: 'GOOGL', group: 'strong', label: '強い会社', dd: -20.4, last: 316.8, hi: 398.12, hi_date: '2026-05-13', since: '2026-10-28', below: true },
  { ticker: 'KRUS<b>', group: 'strong', label: '強い会社', dd: -59.9, last: 30, hi: 75, hi_date: '2026-02-06', since: '2026-10-20', below: true },
  { ticker: 'OKLO', group: 'other', label: 'Hanako30', dd: -28.5, last: 20, hi: 100, since: '2026-10-27', below: false },
] };

test('昨日以降に基準を超えたものが新規・グループ別に分ける', () => {
  const g = norm(app.stockGroups(stocks, '2026-10-28'));
  assert.deepEqual(g.fresh.map(a => a.ticker), ['GOOGL', 'OKLO']);
  assert.deepEqual(g.groups.map(x => x.items.length), [0, 2, 1]);
  assert.deepEqual(norm(app.stockGroups({}, '2026-10-28')), { fresh: [], groups: [] });
});

test('欄の表示・エスケープ', () => {
  const h = app.stockSec(stocks, '2026-10-28');
  assert.match(h, /📉 下落アラート（新規） <span class="n">2<\/span>/);
  assert.match(h, /-20\.4%/);
  assert.match(h, /監視 81 銘柄/);
  assert.match(h, /強い会社（20%以上） 2件/);
  assert.match(h, /基準内に戻りかけ/);
  assert.ok(!h.includes('KRUS<b>'));
});

test('新規が無い日は総数を出す', () => {
  const h = app.stockSec({ ...stocks, alerts: stocks.alerts.slice(1, 2) }, '2026-10-28');
  assert.match(h, /📉 下落アラート <span class="n">1<\/span>/);
  assert.match(h, /新しく基準を超えた銘柄はありません/);
});

test('新規が多い日は8件まで出して残りは折りたたみへ', () => {
  const many = Array.from({ length: 11 }, (_, i) => ({ ticker: 'T' + i, group: 'other', label: 'Hanako30', dd: -31 - i, since: '2026-10-28' }));
  const h = app.stockSec({ ...stocks, alerts: many }, '2026-10-28');
  assert.match(h, /（新規） <span class="n">11<\/span>/);
  assert.match(h, /ほか 3 件は下のグループ別一覧に/);
  assert.equal((h.split('<details>')[0].match(/class="ev sk/g) || []).length, 8);
});

test('投資タブ: 下落アラートと花子の動画を載せ、データが無ければ空表示', () => {
  const h = app.investTab({ stocks, youtube: { items: [{ id: 'a', date: '2026-10-28', title: '動画A', url: 'u' }] } }, '2026-10-28');
  assert.ok(h.indexOf('📉 下落アラート') < h.indexOf('📺 花子の米国株'));
  assert.match(h, /動画A/);
  const e = app.investTab({}, '2026-10-28');
  assert.match(e, /まだ株価のデータがありません/);
  assert.match(e, /直近7日の動画はありません/);
});

test('タブバー: 選択中に印、投資タブに新規の件数', () => {
  const h = app.tabNav('invest', { stocks }, '2026-10-28');
  assert.match(h, /class="tb sel" data-act="tab" data-tab="invest"/);
  assert.match(h, /<span class="badge">2<\/span>/);
  assert.ok(!app.tabNav('home', {}, '2026-10-28').includes('badge'));
});

test('保存したタブを読み戻す・不正な値はホーム', () => {
  const a = loadApp({ today: '2026-10-28T09:00:00+09:00', storage: { 'dh.v1': JSON.stringify({ tab: 'invest' }) } });
  assert.equal(a.loadState().tab, 'invest');
  const b = loadApp({ today: '2026-10-28T09:00:00+09:00', storage: { 'dh.v1': JSON.stringify({ tab: 'x' }) } });
  assert.equal(b.loadState().tab, 'home');
});
