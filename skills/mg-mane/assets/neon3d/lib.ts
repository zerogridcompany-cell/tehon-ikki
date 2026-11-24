// 時間と動きの曲線（B＝ease-out・C＝ease-in-out・D＝ease-in・E＝はね返り）・鍵の補間（pchip）
export const C01 = (x: number) => Math.max(0, Math.min(1, x));
export const B = (x: number) => 1 - Math.pow(1 - C01(x), 3);
export const Cq = (x: number) => { const t = C01(x); return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2; };
export const D = (x: number) => Math.pow(C01(x), 3);
export const E = (x: number) => { const t = C01(x), c1 = 1.70158 * 1.15, c3 = c1 + 1; return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2); };
// 区間 [a,b] の進み（曲線つき）
export const seg = (t: number, a: number, b: number, f: (x: number) => number = Cq) => f((t - a) / (b - a));
// 出て・消える（出る a〜a+din・消える b〜b+dout）
export const inout = (t: number, a: number, b: number, din = 0.2, dout = 0.2, fi = B, fo = Cq) => Math.min(fi((t - a) / din), 1 - fo((t - b) / dout));
export const lerp = (a: number, b: number, u: number) => a + (b - a) * u;
// pchip：鍵 K=[[t, v0, v1, ...]] の j 列目を t で
export const pchip = (K: number[][], t: number, j: number) => {
  const n = K.length; if (t <= K[0][0]) return K[0][j]; if (t >= K[n - 1][0]) return K[n - 1][j];
  let i = 0; while (i < n - 2 && t > K[i + 1][0]) i++;
  const h = (k: number) => K[k + 1][0] - K[k][0], d = (k: number) => (K[k + 1][j] - K[k][j]) / h(k);
  const m = (k: number) => {
    if (k === 0) return d(0); if (k === n - 1) return d(n - 2);
    const a = d(k - 1), b = d(k); if (a * b <= 0) return 0;
    const w1 = 2 * h(k) + h(k - 1), w2 = h(k) + 2 * h(k - 1); return (w1 + w2) / (w1 / a + w2 / b);
  };
  const x0 = K[i][0], x1 = K[i + 1][0], hh = x1 - x0, s = (t - x0) / hh;
  const h00 = 2 * s ** 3 - 3 * s ** 2 + 1, h10 = s ** 3 - 2 * s ** 2 + s, h01 = -2 * s ** 3 + 3 * s ** 2, h11 = s ** 3 - s ** 2;
  return h00 * K[i][j] + h10 * hh * m(i) + h01 * K[i + 1][j] + h11 * hh * m(i + 1);
};
export const keys = (K: number[][], t: number) => K[0].slice(1).map((_, j) => pchip(K, t, j + 1));
// 数を数える（a→b を区間で・整数）
export const count = (t: number, t0: number, t1: number, a: number, b: number, f = B) => Math.round(lerp(a, b, f((t - t0) / (t1 - t0))));
export const yen = (n: number) => n.toLocaleString('en-US');
