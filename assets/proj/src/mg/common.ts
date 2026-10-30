// 動く MG の部品で共通に使う小物（51 の parts/ から抜き出した・2026-10-25）
// 🔴 時刻は全部「コマ」（手本の 0 始まりのコマ番号＝ffmpeg の select n と同じ）。秒で書かん（51 は秒とコマが混ざって1コマずれた）
// 🔴 位置・大きさは全部「画面の px」（cfg.json の width×height）。51 の数字は 1920x1080 の時の値
import {Easing, spring} from 'remotion';

export const cl = (v: number) => Math.max(0, Math.min(1, v));
export const lerp = (a: number, b: number, p: number) => a + (b - a) * p;

// 曲線＝motion-cm の動きの図鑑（ugoki-zukan.md）の名前で呼ぶ。写しでは手本から測った曲線を優先し、名前は「近い物」を選ぶだけ
export const CURVES: Record<string, (p: number) => number> = {
  linear: (p) => p,
  easeOutQuad: (p) => 1 - (1 - p) * (1 - p),
  easeOutCubic: (p) => Easing.out(Easing.cubic)(p),
  easeInCubic: (p) => Easing.in(Easing.cubic)(p),
  easeInOutCubic: (p) => Easing.inOut(Easing.cubic)(p),
  easeOutQuart: (p) => 1 - Math.pow(1 - p, 4),
  easeOutBack: (p) => { const c1 = 1.70158, c3 = c1 + 1; return 1 + c3 * Math.pow(p - 1, 3) + c1 * Math.pow(p - 1, 2); },
  easeOutElastic: (p) => (p === 0 || p === 1 ? p : Math.pow(2, -10 * p) * Math.sin((p * 10 - 0.75) * ((2 * Math.PI) / 3)) + 1),
  easeOutBounce: (p) => Easing.bounce(p),
};
/** 曲線を名前で引く（無い名前は easeOutCubic）。p は 0〜1 に丸めてからかける */
export const curve = (name: string | undefined, p: number) => (CURVES[name ?? 'easeOutCubic'] ?? CURVES.easeOutCubic)(cl(p));
/** spring の値（motion-cm の決まり「spring を使う」）。f＝始まりからのコマ */
export const springAt = (f: number, fps: number, cfg?: {mass?: number; stiffness?: number; damping?: number}) =>
  spring({frame: Math.max(0, f), fps, config: {mass: cfg?.mass ?? 1, stiffness: cfg?.stiffness ?? 100, damping: cfg?.damping ?? 10}});

/** 段の表 [[コマ, 値], …]（コマの小さい順）から、今のコマの値（最後に越えた段）。まだなら undefined */
export function stepAt<T>(table: [number, T][] | undefined, f: number): T | undefined {
  if (!table) return undefined;
  let v: T | undefined;
  for (const [k, x] of table) { if (f >= k) v = x; else break; }
  return v;
}
/** 段の表の行ごと版（[コマ, …残り][]）＝行そのものを返す */
export function rowAt<R extends any[]>(table: R[] | undefined, f: number): R | undefined {
  if (!table) return undefined;
  let v: R | undefined;
  for (const r of table) { if (f >= r[0]) v = r; else break; }
  return v;
}
/** {"<コマ>": 値} の表（手本を毎コマ測った json）から引く */
export const perFrame = <T,>(m: Record<string, T> | undefined, f: number): T | undefined => (m ? m[String(f)] : undefined);
/** 打ち（on twos / threes）：n コマごとに同じ値に丸めたコマ。手本の紙のコラージュは 3（10fps）・札の連打は 2〜3 */
export const onN = (f: number, n = 1, f0 = 0) => (n <= 1 ? f : f0 + Math.floor((f - f0) / n) * n);
