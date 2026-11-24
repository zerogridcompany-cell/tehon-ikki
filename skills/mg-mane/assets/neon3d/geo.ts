// 3D の形（全部コードで作った自作の形＝外の素材なし）。線分の配列 [x0,y0,z0,x1,y1,z1,...]
// goat-mercedes：手本＝@goatexplanations「メルセデスが同じ車を2回売った」。水色の光る線の車（セダン C クラス）・エンジン・棚・台など
export type Seg = number[];
export const push = (a: Seg, p: number[], q: number[]) => a.push(p[0], p[1], p[2], q[0], q[1], q[2]);
export const poly = (a: Seg, pts: number[][], close = true) => { for (let i = 0; i < pts.length - (close ? 0 : 1); i++) push(a, pts[i], pts[(i + 1) % pts.length]); };
// 平面の円（ax＝法線の軸 0:x 1:y 2:z）
export const circle = (a: Seg, c: number[], r: number, ax: number, n = 40, a0 = 0, a1 = Math.PI * 2) => {
  const pts: number[][] = [];
  for (let i = 0; i <= n; i++) {
    const t = a0 + (a1 - a0) * i / n, u = Math.cos(t) * r, v = Math.sin(t) * r;
    pts.push(ax === 2 ? [c[0] + u, c[1] + v, c[2]] : ax === 0 ? [c[0], c[1] + v, c[2] + u] : [c[0] + u, c[1], c[2] + v]);
  }
  poly(a, pts, false);
};
export const boxSeg = (a: Seg, x0: number, x1: number, y0: number, y1: number, z0: number, z1: number) => {
  const v = [[x0, y0, z0], [x1, y0, z0], [x1, y0, z1], [x0, y0, z1], [x0, y1, z0], [x1, y1, z0], [x1, y1, z1], [x0, y1, z1]];
  for (const [i, j] of [[0, 1], [1, 2], [2, 3], [3, 0], [4, 5], [5, 6], [6, 7], [7, 4], [0, 4], [1, 5], [2, 6], [3, 7]]) push(a, v[i], v[j]);
};
const lerp = (a: number, b: number, u: number) => a + (b - a) * u;
// 折れ線をなめらかに（Catmull-Rom）
const smooth = (P: number[][], n = 6): number[][] => {
  const o: number[][] = [];
  for (let i = 0; i < P.length - 1; i++) {
    const p0 = P[Math.max(0, i - 1)], p1 = P[i], p2 = P[i + 1], p3 = P[Math.min(P.length - 1, i + 2)];
    for (let k = 0; k < n; k++) { const t = k / n, t2 = t * t, t3 = t2 * t;
      o.push(p1.map((_, j) => 0.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2 + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3))); }
  }
  o.push(P[P.length - 1]); return o;
};

// ── セダン（C クラス）。前＝＋x・長さ 4.72・幅 1.86・高さ 1.40。車輪は別（回す）
// v6（11/24）：手本の線の車（rf 2.6/3.6/12.0/49.0/61.0 の輪郭）に寄せた＝低く長いボンネット・寝た前の窓・張り出したフェンダー・大きい星と横長のグリル・細い前照灯・下の台形の口
export const WR = 0.35, WXF = 1.42, WXR = -1.42, WZ = 0.82;
export const PROF: number[][] = [[2.33, 0.34], [2.39, 0.5], [2.35, 0.66], [2.1, 0.76], [1.5, 0.84], [0.95, 0.93], [0.6, 1.08], [0.1, 1.36], [-0.5, 1.40], [-1.05, 1.35], [-1.7, 1.06], [-2.2, 1.0], [-2.37, 0.9], [-2.4, 0.55], [-2.32, 0.34]];
export const sedan = (): {body: Seg; red: Seg; wheels: Seg; star: Seg; lamp: Seg} => {
  const a: Seg = [], red: Seg = [], st: Seg = [], lp: Seg = [];
  const P = smooth(PROF, 5);
  const half = (y: number, x: number) => y > 1.0 ? lerp(0.86, 0.68, (y - 1.0) / 0.4) : (Math.abs(x - WXF) < 0.6 || Math.abs(x - WXR) < 0.6 ? 0.93 : 0.9);
  for (const s of [-1, 1]) {
    poly(a, P.map(([x, y]) => [x, y, s * half(y, x)]), false);
    // 下の線（車輪のアーチで切る）＋フェンダーの張り出し（アーチの外にもう 1 本）
    const arch = (cx: number, r: number, z: number) => { const q: number[][] = []; for (let i = 0; i <= 16; i++) { const t = Math.PI - Math.PI * i / 16; q.push([cx + Math.cos(t) * r, 0.36 + Math.sin(t) * r * 0.95, s * z]); } return q; };
    poly(a, [[2.3, 0.34, s * 0.9], [WXF + 0.47, 0.34, s * 0.9]], false); poly(a, arch(WXF, 0.47, 0.92).reverse(), false); poly(a, arch(WXF, 0.53, 0.96), false);
    poly(a, [[WXF - 0.47, 0.34, s * 0.9], [WXR + 0.47, 0.32, s * 0.9]], false); poly(a, arch(WXR, 0.47, 0.92).reverse(), false); poly(a, arch(WXR, 0.53, 0.96), false);
    poly(a, [[WXR - 0.47, 0.34, s * 0.9], [-2.3, 0.34, s * 0.9]], false);
    // 敷居の線（下の黒い帯）
    poly(a, [[WXF - 0.5, 0.42, s * 0.9], [WXR + 0.5, 0.42, s * 0.9]], false);
    // 窓（DLO）と柱
    const win = smooth([[0.62, 1.0], [0.1, 1.31], [-0.5, 1.35], [-1.02, 1.3], [-1.6, 1.04], [0.62, 1.0]], 4).map(([x, y]) => [x, y, s * (y > 1.0 ? lerp(0.86, 0.7, (y - 1.0) / 0.4) : 0.88)]);
    poly(a, win, false);
    push(a, [-0.38, 1.0, s * 0.88], [-0.46, 1.35, s * 0.71]); push(a, [-0.3, 1.0, s * 0.88], [-0.38, 1.35, s * 0.71]);
    // 肩の線（キャラクターライン 2 本）・ドアの切れ目・取っ手
    poly(a, smooth([[2.2, 0.74], [1.0, 0.86], [-1.2, 0.9], [-2.32, 0.88]], 5).map(([x, y]) => [x, y, s * 0.91]), false);
    poly(a, smooth([[1.9, 0.58], [0.6, 0.6], [-1.6, 0.66]], 4).map(([x, y]) => [x, y, s * 0.92]), false);
    push(a, [0.68, 0.42, s * 0.9], [0.7, 0.99, s * 0.9]); push(a, [-0.36, 0.42, s * 0.9], [-0.34, 1.0, s * 0.9]); push(a, [-1.3, 0.42, s * 0.9], [-1.36, 1.02, s * 0.9]);
    push(a, [0.3, 0.82, s * 0.92], [0.5, 0.82, s * 0.92]); push(a, [-0.75, 0.84, s * 0.92], [-0.55, 0.84, s * 0.92]);
    // 前照灯（細い斜めの帯・白く光る）と尾灯（赤）
    poly(lp, [[2.33, 0.68, s * 0.84], [2.12, 0.77, s * 0.9], [2.06, 0.74, s * 0.66], [2.3, 0.66, s * 0.5]], true);
    push(lp, [2.3, 0.67, s * 0.78], [2.13, 0.74, s * 0.82]);
    poly(red, [[-2.33, 0.92, s * 0.86], [-2.1, 0.99, s * 0.88], [-2.14, 0.93, s * 0.55], [-2.38, 0.86, s * 0.42]], true);
    push(red, [-2.36, 0.9, s * 0.7], [-2.15, 0.96, s * 0.72]);
    // ミラー
    poly(a, [[0.62, 1.0, s * 0.9], [0.52, 1.1, s * 1.07], [0.36, 1.1, s * 1.07], [0.42, 1.0, s * 0.9]], true);
    // 前のフェンダーの山（ボンネットより高い）
    poly(a, smooth([[2.15, 0.76], [1.5, 0.86], [0.95, 0.93]], 4).map(([x, y]) => [x, y + 0.03, s * 0.78]), false);
  }
  // 横をつなぐ線（輪郭の点を何か所か）
  for (const i of [0, 3, 8, 12, 18, 25, 32, 38, 45, 50, 56, 62, 66, 70]) { const p = P[Math.min(i, P.length - 1)]; const z = half(p[1], p[0]); push(a, [p[0], p[1], -z], [p[0], p[1], z]); }
  // フロントガラス・リアガラスの縁、ボンネットの 2 本の折り目、屋根の縁
  poly(a, [[0.92, 0.95, -0.84], [0.12, 1.34, -0.7], [0.12, 1.34, 0.7], [0.92, 0.95, 0.84]], true);
  poly(a, [[-1.05, 1.34, -0.7], [-1.7, 1.05, -0.84], [-1.7, 1.05, 0.84], [-1.05, 1.34, 0.7]], true);
  for (const s of [-1, 1]) { poly(a, smooth([[2.25, 0.72, s * 0.3], [1.5, 0.83, s * 0.36], [0.95, 0.94, s * 0.42]].map((v) => v), 3), false); push(a, [0.12, 1.36, s * 0.66], [-1.05, 1.36, s * 0.66]); }
  // 顔：横長のグリル（2 重の枠）＋中の横線＋大きい星・下の台形の口
  poly(a, [[2.39, 0.44, -0.5], [2.39, 0.65, -0.52], [2.39, 0.65, 0.52], [2.39, 0.44, 0.5]], true);
  poly(a, [[2.4, 0.47, -0.45], [2.4, 0.62, -0.47], [2.4, 0.62, 0.47], [2.4, 0.47, 0.45]], true);
  for (const y of [0.505, 0.585]) { push(a, [2.4, y, -0.45], [2.4, y, -0.17]); push(a, [2.4, y, 0.17], [2.4, y, 0.45]); }
  circle(st, [2.42, 0.55, 0], 0.15, 0, 40); circle(st, [2.42, 0.55, 0], 0.135, 0, 40);
  for (let k = 0; k < 3; k++) { const t = Math.PI / 2 + k * Math.PI * 2 / 3; push(st, [2.42, 0.55, 0], [2.42, 0.55 + Math.sin(t) * 0.135, Math.cos(t) * 0.135]); }
  poly(a, [[2.36, 0.4, -0.78], [2.33, 0.3, -0.66], [2.33, 0.3, 0.66], [2.36, 0.4, 0.78]], true);
  for (const s of [-1, 1]) poly(a, [[2.37, 0.36, s * 0.82], [2.3, 0.62, s * 0.9]], false);
  return {body: a, red, wheels: wheels(), star: st, lamp: lp};
};
// 車輪 4 つ（回す時は別の group）：タイヤ＝外と内の輪＋つなぐ線（円柱に見える）・ホイール＝10 本の細いスポーク（5 対）
export const wheelOne = (s: number): Seg => {
  const a: Seg = []; const zo = s * WZ + s * 0.11, zi = s * WZ - s * 0.13;
  circle(a, [0, 0, zo], WR, 2, 44); circle(a, [0, 0, zi], WR, 2, 44); circle(a, [0, 0, zo + s * 0.005], WR * 0.74, 2, 40); circle(a, [0, 0, zo + s * 0.02], WR * 0.16, 2, 16);
  for (let k = 0; k < 12; k++) { const t = k * Math.PI / 6; push(a, [Math.cos(t) * WR, Math.sin(t) * WR, zo], [Math.cos(t) * WR, Math.sin(t) * WR, zi]); }
  for (let k = 0; k < 5; k++) { const t = Math.PI / 2 + k * Math.PI * 2 / 5; for (const d of [-0.16, 0.16]) push(a, [Math.cos(t + d * 0.5) * WR * 0.16, Math.sin(t + d * 0.5) * WR * 0.16, zo + s * 0.02], [Math.cos(t + d) * WR * 0.72, Math.sin(t + d) * WR * 0.72, zo + s * 0.006]); }
  return a;
};
const wheels = (): Seg => [];
export const caliper = (s: number): Seg => { const a: Seg = []; circle(a, [0, 0, s * WZ + s * 0.06], WR * 0.55, 2, 10, 0.3, 1.1); circle(a, [0, 0, s * WZ + s * 0.06], WR * 0.48, 2, 10, 0.3, 1.1); return a; };

// ── 道（2 本の車線）・床のはしご模様・山形の印
export const ladder = (x0: number, x1: number, z0: number, z1: number, n: number): Seg => { const a: Seg = []; for (let i = 0; i <= n; i++) { const z = lerp(z0, z1, i / n); push(a, [x0, 0.01, z], [x1, 0.01, z]); } return a; };
export const chevron = (x: number, z: number, w = 0.5): Seg => { const a: Seg = []; poly(a, [[x - w, 0.01, z], [x, 0.01, z - w * 0.45], [x + w, 0.01, z]], false); return a; };
// 枠（ドア）：手前の四角と奥の四角
export const frame = (w: number, h: number, d: number): Seg => { const a: Seg = []; boxSeg(a, -w / 2, w / 2, 0, h, -d, 0); return a; };
// 街灯（L 字）
export const lamp = (h = 4.2): Seg => { const a: Seg = []; push(a, [0, 0, 0], [0, h, 0]); push(a, [0, h, 0], [0.7, h + 0.15, 0]); push(a, [0.08, 0, 0], [0.08, h - 0.05, 0]); return a; };

// ── V6 エンジン：下の箱・V の 2 つの列（水色）・上の頭（赤）・吸気の箱
export const engine = (): {cyan: Seg; red: Seg; holes: number[][]} => {
  const c: Seg = [], r: Seg = [], holes: number[][] = [];
  boxSeg(c, -0.9, 0.9, 0, 0.9, -1.1, 1.1);      // 下の箱
  circle(c, [0, 0.45, 1.1], 0.38, 2, 32);           // 前のプーリー
  const A = 0.55;
  for (const s of [-1, 1]) {
    const vx = s * Math.sin(A), vy = Math.cos(A), ux = s * Math.cos(A), uy = -Math.sin(A);
    const P = (u: number, v: number, z: number) => [s * 0.32 + u * ux + v * vx, 0.9 + u * uy + v * vy, z];
    const bx = (u0: number, u1: number, v0: number, v1: number, seg: Seg) => {
      const ps = [[u0, v0], [u1, v0], [u1, v1], [u0, v1]];
      for (const z of [-1.0, 1.0]) poly(seg, ps.map(([u, v]) => P(u, v, z)), true);
      for (const [u, v] of ps) push(seg, P(u, v, -1.0), P(u, v, 1.0));
    };
    bx(-0.34, 0.34, 0, 0.95, c);                      // シリンダーの列（水色）
    bx(-0.4, 0.4, 0.95, 1.25, r);                     // 頭（赤）
    for (let k = 0; k < 7; k++) { const z = -0.9 + k * 0.3; push(r, P(-0.4, 1.25, z), P(0.4, 1.25, z)); }
    for (let k = 0; k < 3; k++) holes.push(P(0, 1.27, -0.66 + k * 0.66));
  }
  boxSeg(c, -0.26, 0.26, 1.55, 1.95, -0.3, 0.3);   // 吸気の箱
  return {cyan: c, red: r, holes};
};
// ターボ（オレンジの丸＝貝の形）
export const turbo = (): Seg => { const a: Seg = []; circle(a, [0, 0, 0], 0.3, 2, 36); circle(a, [0, 0, 0.18], 0.3, 2, 36); circle(a, [0, 0, 0.18], 0.12, 2, 20); for (let k = 0; k < 8; k++) { const t = k * Math.PI / 4; push(a, [Math.cos(t) * 0.12, Math.sin(t) * 0.12, 0.19], [Math.cos(t + 0.5) * 0.28, Math.sin(t + 0.5) * 0.28, 0.19]); } return a; };
// 歯車（平面）
export const cog = (R = 0.5, n = 14): Seg => { const a: Seg = []; const pts: number[][] = [];
  for (let i = 0; i < n; i++) { const t0 = i * Math.PI * 2 / n, d = Math.PI / n; pts.push([Math.cos(t0 - d * 0.5) * R, Math.sin(t0 - d * 0.5) * R, 0], [Math.cos(t0 - d * 0.3) * R * 1.16, Math.sin(t0 - d * 0.3) * R * 1.16, 0], [Math.cos(t0 + d * 0.3) * R * 1.16, Math.sin(t0 + d * 0.3) * R * 1.16, 0], [Math.cos(t0 + d * 0.5) * R, Math.sin(t0 + d * 0.5) * R, 0]); }
  poly(a, pts, true); circle(a, [0, 0, 0], R * 0.42, 2, 28); return a; };
// 台（白い光る縁の机）
export const table = (L: number, D: number, H: number): Seg => { const a: Seg = []; boxSeg(a, -L / 2, L / 2, H - 0.08, H, -D / 2, D / 2); for (const x of [-L / 2 + 0.08, L / 2 - 0.08]) for (const z of [-D / 2 + 0.08, D / 2 - 0.08]) push(a, [x, 0, z], [x, H - 0.08, z]); return a; };
// 棚（白い枠・段 2 つ）
export const shelf = (L: number, D: number, H: number): Seg => { const a: Seg = []; for (const y of [0.05, H * 0.5, H]) { poly(a, [[-L / 2, y, -D / 2], [L / 2, y, -D / 2], [L / 2, y, D / 2], [-L / 2, y, D / 2]], true); } for (const x of [-L / 2, L / 2]) for (const z of [-D / 2, D / 2]) push(a, [x, 0, z], [x, H, z]); return a; };
// シフトレバーの台（白い箱）
export const gate = (): Seg => { const a: Seg = []; boxSeg(a, -0.9, 0.9, 0, 0.32, -0.6, 0.6); poly(a, [[-0.35, 0.33, -0.2], [0.35, 0.33, -0.2], [0.35, 0.33, 0.2], [-0.35, 0.33, 0.2]], true); return a; };
// ロボットの腕（黄）：土台の輪＋2 本の腕（角度で）
export const ring = (r = 1, n = 96): Seg => { const a: Seg = []; circle(a, [0, 0, 0], r, 1, n); return a; };
// ノートパソコン
export const laptop = (): Seg => { const a: Seg = []; poly(a, [[-0.7, 0, -0.45], [0.7, 0, -0.45], [0.7, 0, 0.45], [-0.7, 0, 0.45]], true); poly(a, [[-0.7, 0.04, -0.45], [0.7, 0.04, -0.45], [0.7, 0.04, 0.45], [-0.7, 0.04, 0.45]], true); poly(a, [[-0.7, 0.04, -0.45], [-0.7, 0.9, -0.62], [0.7, 0.9, -0.62], [0.7, 0.04, -0.45]], false); return a; };
// OBD の差し口（台形の箱）
export const obd = (): Seg => { const a: Seg = []; const f = [[-0.6, 0.3], [0.6, 0.3], [0.45, -0.25], [-0.45, -0.25]]; for (const z of [0, -0.5]) poly(a, f.map(([x, y]) => [x, y, z]), true); for (const [x, y] of f) push(a, [x, y, 0], [x, y, -0.5]); poly(a, [[-0.48, 0.2, 0.01], [0.48, 0.2, 0.01], [0.37, -0.16, 0.01], [-0.37, -0.16, 0.01]], true); return a; };
// 枯れ草の玉（ばらばらの線）
export const tumble = (n = 70, seed = 3): Seg => { const a: Seg = []; let s = seed; const r = () => ((s = (s * 16807) % 2147483647) / 2147483647);
  for (let i = 0; i < n; i++) { const t1 = r() * Math.PI * 2, p1 = Math.acos(2 * r() - 1), t2 = t1 + (r() - 0.5) * 2.4, p2 = p1 + (r() - 0.5) * 2.0; const S = (t: number, p: number) => [Math.sin(p) * Math.cos(t) * 0.5, Math.cos(p) * 0.5, Math.sin(p) * Math.sin(t) * 0.5]; push(a, S(t1, p1), S(t2, p2)); } return a; };
// 小旗の紐（三角の旗）
export const bunting = (L: number, n: number): {line: Seg; flags: Seg[]} => { const line: Seg = []; const flags: Seg[] = [[], []]; const y = (x: number) => -0.25 * Math.cos((x / L) * Math.PI * 2 * 2) * 0.5;
  for (let i = 0; i < 80; i++) push(line, [-L / 2 + L * i / 80, y(-L / 2 + L * i / 80), 0], [-L / 2 + L * (i + 1) / 80, y(-L / 2 + L * (i + 1) / 80), 0]);
  for (let i = 0; i < n; i++) { const x = -L / 2 + L * (i + 0.5) / n; poly(flags[i % 2], [[x - 0.18, y(x), 0], [x + 0.18, y(x), 0], [x, y(x) - 0.32, 0]], true); }
  return {line, flags}; };
// ハート
export const heart = (): Seg => { const a: Seg = []; const pts: number[][] = []; for (let i = 0; i <= 48; i++) { const t = i / 48 * Math.PI * 2; pts.push([0.016 * 16 * Math.sin(t) ** 3, 0.016 * (13 * Math.cos(t) - 5 * Math.cos(2 * t) - 2 * Math.cos(3 * t) - Math.cos(4 * t)), 0]); } poly(a, pts, false); return a; };
// 螺旋（2 台の車の間の DNA のような線）
export const helix = (L: number, r: number, turns: number, ph = 0): Seg => { const a: Seg = []; const n = 160; for (let i = 0; i < n; i++) { const u0 = i / n, u1 = (i + 1) / n; const P = (u: number) => [lerp(-L / 2, L / 2, u), r * Math.sin(u * turns * Math.PI * 2 + ph), r * Math.cos(u * turns * Math.PI * 2 + ph)]; push(a, P(u0), P(u1)); } return a; };
