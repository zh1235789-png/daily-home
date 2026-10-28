// 筋トレAIコーチの index.html から WEEK_PLAN と DAY_MENUS を取り出し、JSON で標準出力へ書く。
// 曜日ごとのラン・筋トレの正本はコーチ側なので、ここでは写さずに毎回読む。
//   node build/extract_training.mjs ~/workout-ai-coach/index.html
import { readFileSync } from 'node:fs';
import vm from 'node:vm';

const html = readFileSync(process.argv[2], 'utf8');

function literal(name, close) {
  const start = html.indexOf('const ' + name + ' = ');
  if (start < 0) throw new Error(name + ' が見つかりません');
  const end = html.indexOf('\n' + close, start);
  if (end < 0) throw new Error(name + ' の終わりが見つかりません');
  const src = html.slice(start + ('const ' + name + ' = ').length, end + 1 + close.length - 1);
  return vm.runInNewContext('(' + src + ')', {}, { timeout: 1000 });
}

const plan = literal('WEEK_PLAN', '];');
const menus = literal('DAY_MENUS', '};');
process.stdout.write(JSON.stringify({ plan, menus }));
