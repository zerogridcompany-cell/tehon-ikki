// mg-mane の「滑らか」：keys.json（scripts/ease_fit.py）の曲線を Remotion で連続に評価する。
// 使い方：作業の proj/src/<場面>/ に写して import {kfAt, vel, tau, mblur, ...} from './ease'
//   kfAt(f, K)        … K（keys.json の中身）の値を f コマで。区間の中は曲線（線形の表にせん）・止まる時はバネの尾
//   vel(f, K)         … そのコマで動いた量（f-1→f・単位は K の単位/コマ）＝ブレの長さ・音の時刻に使う
//   tau(f, warp)      … 手本の中の時間（warp=9：9 コマごとに 1 コマ飛ぶ。tehonN で実測）
//   mblur(vx, vy, k)  … 向きつきのブレ（SVG feGaussianBlur の stdDeviation "sx sy"）。k＝手本の縁のぼけ÷速さ（tehonN は 0.28〜0.29＝1 コマ分のシャッター）。floor の既定 0＝連続（しきいで付け外しすると、その 1 コマで字の描き方が変わって跳ぶ）
//   ez(kind, u, p)    … 0..1 の曲線を直に（u は 0..1）。tw(f, a, b, ease) … a→b コマを曲線で 0..1
//   sgT(tab)          … コマごとの表を τ の上で 2 次の局所回帰（Savitzky–Golay 7 と同じ重み）＝測りのゆれだけ消す
// 決まり：位置は小数のまま（Math.round 禁止）・隣のコマで同じ値を作らん（動いとる間は必ず動く）

export type Ease =
  | {kind: 'linear'}
  | {kind: 'pow_out' | 'pow_in' | 'pow_inout'; n: number}
  | {kind: 'expo_out'; k: number}
  | {kind: 'bezier'; x1: number; y1: number; x2: number; y2: number}
  | {kind: 'back_out'; c: number}
  | {kind: 'bounce'}
  | {kind: 'spring'; w: number; z: number; v0?: number}
  | {kind: 'smooth'};
export type Seg =
  | {kind: 'move'; t0: number; t1: number; from: number; to: number; ease: Ease}
  | {kind: 'hold'; t0: number; t1: number; v: number};
export type Keys = {name?: string; warp?: number; segs: Seg[]};

export const tau = (f: number, warp = 0): number => {
  if (!warp) return f;
  const n = Math.floor(f), fr = f - n;
  const a = n + Math.floor(n / warp), b = n + 1 + Math.floor((n + 1) / warp);
  return a + (b - a) * fr;
};

const C01 = (x: number) => Math.min(1, Math.max(0, x));

const bez = (u: number, x1: number, y1: number, x2: number, y2: number) => {
  // CSS cubic-bezier：x(s)=u を解いて y(s)
  let s = u;
  for (let i = 0; i < 8; i++) {
    const x = 3 * (1 - s) * (1 - s) * s * x1 + 3 * (1 - s) * s * s * x2 + s * s * s - u;
    const dx = 3 * (1 - s) * (1 - s) * x1 + 6 * (1 - s) * s * (x2 - x1) + 3 * s * s * (1 - x2);
    if (Math.abs(x) < 1e-7) break;
    s = C01(s - x / (Math.abs(dx) < 1e-6 ? 1e-6 : dx));
  }
  let lo = 0, hi = 1;
  for (let i = 0; i < 30; i++) {
    const x = 3 * (1 - s) * (1 - s) * s * x1 + 3 * (1 - s) * s * s * x2 + s * s * s;
    if (Math.abs(x - u) < 1e-6) break;
    if (x < u) lo = s; else hi = s;
    s = (lo + hi) / 2;
  }
  return 3 * (1 - s) * (1 - s) * s * y1 + 3 * (1 - s) * s * s * y2 + s * s * s;
};

const bounceOut = (u: number) => {
  const n1 = 7.5625, d1 = 2.75;
  if (u < 1 / d1) return n1 * u * u;
  if (u < 2 / d1) return n1 * (u - 1.5 / d1) ** 2 + 0.75;
  if (u < 2.5 / d1) return n1 * (u - 2.25 / d1) ** 2 + 0.9375;
  return n1 * (u - 2.625 / d1) ** 2 + 0.984375;
};

/** 0→1 のバネ。t は τ コマ（区間の頭から）・w は 1 コマあたりの角速度・z は減衰比・v0 は初めの速さ */
export const springT = (t: number, w: number, z: number, v0 = 0): number => {
  if (t <= 0) return 0;
  if (z < 0.999) {
    const wd = w * Math.sqrt(1 - z * z);
    return 1 - Math.exp(-z * w * t) * (Math.cos(wd * t) + ((z * w - v0) / wd) * Math.sin(wd * t));
  }
  if (z <= 1.001) return 1 - Math.exp(-w * t) * (1 + (w - v0) * t);
  const r1 = -w * (z - Math.sqrt(z * z - 1)), r2 = -w * (z + Math.sqrt(z * z - 1));
  const B = (v0 + r1) / (r2 - r1), A = -1 - B;
  return 1 + A * Math.exp(r1 * t) + B * Math.exp(r2 * t);
};

/** 0..1 の曲線（spring は u ではなく t を使うので ez では使わん） */
export const ez = (e: Ease, u0: number): number => {
  const u = C01(u0);
  switch (e.kind) {
    case 'linear': return u;
    case 'smooth': return u * u * (3 - 2 * u);
    case 'pow_out': return 1 - Math.pow(1 - u, e.n);
    case 'pow_in': return Math.pow(u, e.n);
    case 'pow_inout': return u < 0.5 ? 0.5 * Math.pow(2 * u, e.n) : 1 - 0.5 * Math.pow(2 - 2 * u, e.n);
    case 'expo_out': return (1 - Math.exp(-e.k * u)) / (1 - Math.exp(-e.k));
    case 'bezier': return bez(u, e.x1, e.y1, e.x2, e.y2);
    case 'back_out': return 1 + (e.c + 1) * Math.pow(u - 1, 3) + e.c * Math.pow(u - 1, 2);
    case 'bounce': return bounceOut(u);
    case 'spring': return springT(u * 30, e.w, e.z, e.v0 ?? 0); // 予備（spring は kfAt で t を使う）
  }
};

/** keys の値（f は手本のコマ・小数可） */
export const kfAt = (f: number, K: Keys): number => {
  const w = K.warp ?? 0, t = tau(f, w), S = K.segs;
  if (!S.length) return 0;
  let act: Seg | null = null;
  for (const s of S) if (tau(s.t0, w) <= t + 1e-9) act = s;
  if (!act) { const s = S[0]; return s.kind === 'hold' ? s.v : s.from; }
  if (act.kind === 'hold') return act.v;
  const T0 = tau(act.t0, w), T1 = tau(act.t1, w);
  if (act.ease.kind === 'spring') return act.from + (act.to - act.from) * springT(t - T0, act.ease.w, act.ease.z, act.ease.v0 ?? 0);
  return act.from + (act.to - act.from) * ez(act.ease, (t - T0) / Math.max(T1 - T0, 1e-6));
};

/** f-1 → f で動いた量 */
export const vel = (f: number, K: Keys): number => kfAt(f, K) - kfAt(f - 1, K);

/** a→b コマを曲線で 0..1（warp つき）。spring の時は t を τ コマで数える */
export const tw = (f: number, a: number, b: number, e: Ease = {kind: 'smooth'}, warp = 0): number => {
  const t = tau(f, warp), A = tau(a, warp), B = tau(b, warp);
  if (e.kind === 'spring') return springT(t - A, e.w, e.z, e.v0 ?? 0);
  return ez(e, (t - A) / Math.max(B - A, 1e-6));
};

/** 向きつきのブレ：手本の速いコマの縁のぼけ σ ≒ k×速さ（px/コマ）。小さい時は 0（くっきり） */
export const mblur = (vx: number, vy: number, k = 0.3, floor = 0, max = 40): string => {
  const sx = Math.min(max, Math.abs(vx) * k), sy = Math.min(max, Math.abs(vy) * k);
  return `${(sx < floor ? 0 : sx).toFixed(2)} ${(sy < floor ? 0 : sy).toFixed(2)}`;
};

/** コマごとの表 {"コマ":[値…]} を τ の上で 2 次の局所回帰（窓 half=3 で SG7 相当）。切れ目 cuts の前後はまたがん */
export const sgT = (tab: Record<string, number[]>, warp = 9, half = 3, cuts: number[] = []): Record<string, number[]> => {
  const ks = Object.keys(tab).map(Number).sort((a, b) => a - b);
  const out: Record<string, number[]> = {};
  const side = (k: number) => cuts.filter((c) => k >= c).length;
  for (let i = 0; i < ks.length; i++) {
    const k = ks[i], sk = side(k);
    const idx: number[] = [];
    for (let j = Math.max(0, i - half); j <= Math.min(ks.length - 1, i + half); j++) if (side(ks[j]) === sk) idx.push(j);
    const t0 = tau(k, warp), dim = tab[String(k)].length, res: number[] = [];
    for (let d = 0; d < dim; d++) {
      // 2 次の最小二乗（x＝τ−τ0）
      let s0 = 0, s1 = 0, s2 = 0, s3 = 0, s4 = 0, y0 = 0, y1 = 0, y2 = 0;
      for (const j of idx) {
        const x = tau(ks[j], warp) - t0, y = tab[String(ks[j])][d];
        s0 += 1; s1 += x; s2 += x * x; s3 += x * x * x; s4 += x * x * x * x; y0 += y; y1 += x * y; y2 += x * x * y;
      }
      if (idx.length < 4) { res.push(tab[String(k)][d]); continue; }
      const det = s0 * (s2 * s4 - s3 * s3) - s1 * (s1 * s4 - s3 * s2) + s2 * (s1 * s3 - s2 * s2);
      if (Math.abs(det) < 1e-12) { res.push(tab[String(k)][d]); continue; }
      const a0 = (y0 * (s2 * s4 - s3 * s3) - s1 * (y1 * s4 - s3 * y2) + s2 * (y1 * s3 - s2 * y2)) / det;
      res.push(a0);
    }
    out[String(k)] = res;
  }
  return out;
};
