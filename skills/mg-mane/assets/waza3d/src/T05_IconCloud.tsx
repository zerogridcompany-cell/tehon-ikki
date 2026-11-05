// T05 IconCloud（手札 R1_09・道 A＝2D の投影の式）
// compreel「Icon Cloud Intro」の motion_params.json の式をそのまま移植（MIT・作者が AE／Blender でも同じ数字で動かす）：
// カメラ＝中心の印から対数空間で 2 段の引き／44 個は各自の奥行き Z から共通の落ち着き曲線（軽い行き過ぎ）で 9x5 に着地・半分は自転
// 最後は exp(A(t)(r/1000)^p) で外へ（遠いほど速い）＋最後の 3 コマだけシャッターを開く（副コマを重ねる）→ 題が下から上がる。
import React from 'react';
import {AbsoluteFill, Img, staticFile, useCurrentFrame, useVideoConfig, Easing} from 'remotion';
import {FONT, clamp01} from './lib';
import MP from './t05_params.json';

export type T05Props = {centerIcon: string; slots: Record<string, string>; line1: string; line2: string; line1Color: string; line2Color: string; bg: string; gradient: string};
const M: any = MP;
const ICONS: Record<string, string> = {"22":"balloons","23":"globe","10":"sunglasses","29":"backpack","13":"light-bulb","16":"bar-chart","32":"succulent","31":"gift-box","0":"microphone","1":"padlock","2":"price-tag","3":"trophy","4":"game-controller","5":"desk-lamp","6":"paper-plane","7":"megaphone","8":"avocado","9":"sneaker","11":"parcel","12":"umbrella","14":"rocket","15":"shopping-bag","17":"croissant","19":"mug","20":"compass","21":"cupcake","24":"magnifier","25":"notebook","26":"gem","27":"key","28":"star","30":"pencil","33":"laptop","34":"instant-camera","35":"puzzle-piece","36":"chat-bubble","37":"paint-palette","38":"paperclip","39":"speaker","40":"desk-calendar","41":"headphones","42":"clapperboard","43":"stopwatch","44":"rubber-duck"};
const slotsDefault: Record<string, string> = {};
for (const [k, v] of Object.entries(ICONS)) slotsDefault[k] = `icons/${v}.png`;
// ZeroGrid：中心のまわり 4 つを達磨に
Object.assign(slotsDefault, {'22': 'zg/daruma_red.png', '23': 'zg/daruma_yellow.png', '13': 'zg/daruma_blue.png', '16': 'zg/daruma_brown.png'});
export const t05Defaults: T05Props = {centerIcon: 'zg/zg_mark.svg', slots: slotsDefault, line1: 'Japan.', line2: '125 million people.', line1Color: '#1b1b1f', line2Color: '#f06433', bg: 'icons/bg.png', gradient: 'icons/gradient.png'};
const src = (s: string) => (s.startsWith('http') ? s : staticFile(s));

const bz = (x1: number, y1: number, x2: number, y2: number) => Easing.bezier(x1, y1, x2, y2);
const ease = (spec: any, u: number) => (spec === 'linear' ? clamp01(u) : bz(spec.bezier[0], spec.bezier[1], spec.bezier[2], spec.bezier[3])(clamp01(u)));
const segVal = (segs: any[], f: number) => {
  const s = segs.find((s) => s.f0 <= f && f <= s.f1) ?? (f < segs[0].f0 ? segs[0] : segs[segs.length - 1]);
  const u = (Math.min(Math.max(f, s.f0), s.f1) - s.f0) / Math.max(s.f1 - s.f0, 1e-9); const e = ease(s.ease, u);
  return s.space === 'log' ? Math.exp(Math.log(s.from) + (Math.log(s.to) - Math.log(s.from)) * e) : s.from + (s.to - s.from) * e;
};
// 止まり 0：46 コマ以降も引きをごく薄く続ける（元は 46 で止める）
const camDn = (f: number) => (segVal(M.camera_dn, Math.min(f, 46)) / segVal(M.camera_dn, 46)) * (1 + Math.max(0, Math.min(f, 54) - 46) * 0.0025);
const interpTab = (tab: Record<string, number>, f: number, before = 0) => {
  const ks = Object.entries(tab).map(([k, v]) => [parseFloat(k), v] as [number, number]).sort((a, b) => a[0] - b[0]);
  if (f <= ks[0][0]) return f < ks[0][0] ? before : ks[0][1];
  const L = ks.length; if (f >= ks[L - 1][0]) return L > 1 ? ks[L - 1][1] + (ks[L - 1][1] - ks[L - 2][1]) * (f - ks[L - 1][0]) : ks[L - 1][1];
  for (let i = 0; i < L - 1; i++) if (f <= ks[i + 1][0]) { const t = (f - ks[i][0]) / (ks[i + 1][0] - ks[i][0]); return ks[i][1] + (ks[i + 1][1] - ks[i][1]) * t; }
  return ks[L - 1][1];
};
const rush = (f: number, r: number) => (f <= 54 ? 1 : Math.exp(interpTab(M.rush.A, f) * Math.pow(r / 1000, M.rush.p)));
const opac = (f: number) => (f <= 55 ? 1 : clamp01(interpTab(M.opacity, f)));
const polyval = (c: number[], x: number) => c.reduce((a, b) => a * x + b, 0);
const spin = (slot: any, f: number) => { const R = slot.rot; if (!R) return 0; const ff = Math.min(Math.max(f, R.t_from), R.t_to); let v = polyval(R.poly, ff - 46); if (f > R.t_to) v += R.slope_after * (f - R.t_to); return v; };
const C = M.grid.center, DX = M.grid.dx, DY = M.grid.dy;

type Pose = {x: number; y: number; k: number; op: number; rot: number};
const pose = (slot: any, fr: number): Pose | null => {
  const depth = slot.Z * (1 - ease(M.settle_ease, (fr - slot.t0) / (slot.t1 - slot.t0)));
  const den = camDn(fr) - depth; if (den <= 0.03) return null;
  const gx = slot.col * DX, gy = slot.row * DY, r = Math.hypot(gx, gy), q = rush(fr, r);
  return {x: C[0] + (gx * q) / den, y: C[1] + (gy * q) / den, k: q / den, op: opac(fr), rot: spin(slot, fr)};
};

export const T05_IconCloud: React.FC<Partial<T05Props>> = (props) => {
  const p = {...t05Defaults, ...props};
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const fr = f * (M.fps / fps); // 手本の 24fps の時間へ（秒は同じ）
  const shutter = fr >= 54 && fr <= 58 ? interpTab(M.shutter, fr) : 0;
  const N = shutter > 0 ? 7 : 1;
  const iconK = fr <= 54 ? 1 / camDn(fr) : interpTab({'54': 1, ...M.icon_growth}, fr);
  const iconOp = opac(fr) * (fr > 56 ? Math.max(0, 1 - (fr - 56)) : 1);
  const gOp = interpTab({'0': 0, '57': 0, '58': 0.05, '64': 0.35, '70': 0.65, '78': 1, '99': 1}, fr);
  const l1 = Easing.bezier(0.2, 0.7, 0.3, 1)(clamp01((fr - 58) / 12));
  const l2 = Easing.bezier(0.2, 0.8, 0.3, 1)(clamp01((fr - 63) / 10));
  const ids = Object.keys(M.slots).filter((id) => p.slots[id]).sort((a, b) => M.slots[a].Z - M.slots[b].Z);
  return (
    <AbsoluteFill style={{overflow: 'hidden'}}>
      <Img src={src(p.bg)} style={{position: 'absolute', width: 1920, height: 1080}} />
      <Img src={src(p.gradient)} style={{position: 'absolute', width: 1920, height: 1080, opacity: gOp}} />
      {/* 中心の印（白い角丸の札） */}
      <div style={{position: 'absolute', left: C[0] - 42, top: C[1] - 42, width: 84, height: 84, borderRadius: 20, background: '#fff', opacity: iconOp,
        transform: `scale(${iconK})`, boxShadow: '0 6px 16px rgba(30,30,60,.12), 0 1px 3px rgba(30,30,60,.08)', display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
        <Img src={src(p.centerIcon)} style={{width: 58}} />
      </div>
      {ids.map((id) => {
        const slot = M.slots[id], sz = M.slot_size_px[id];
        const base = Math.min(sz.foot_w, sz.foot_h) * 1.08; // 足の大きさ（元の正規化に近い）
        const out: React.ReactNode[] = [];
        for (let j = 0; j < N; j++) {
          const t = N === 1 ? fr : fr - shutter * (j / (N - 1)) * (M.fps / fps);
          const P = pose(slot, t); if (!P || P.op <= 0) continue;
          const w = base * P.k;
          out.push(<Img key={j} src={src(p.slots[id])} style={{position: 'absolute', left: P.x - w / 2, top: P.y - w / 2, width: w, height: w, objectFit: 'contain',
            opacity: P.op / N * (N > 1 ? 1.6 : 1), transform: `rotate(${P.rot}deg)`}} />);
        }
        return <React.Fragment key={id}>{out}</React.Fragment>;
      })}
      {/* 題（1 行目 15px 上がって出る・2 行目 57px 下から） */}
      <div style={{position: 'absolute', top: 455, width: '100%', textAlign: 'center', fontFamily: FONT, fontWeight: 600, fontSize: 60, letterSpacing: '-0.01em',
        color: p.line1Color, opacity: l1, transform: `translateY(${15 * (1 - l1)}px)`}}>{p.line1}</div>
      <div style={{position: 'absolute', top: 530, width: '100%', textAlign: 'center', fontFamily: FONT, fontWeight: 600, fontSize: 60, letterSpacing: '-0.01em',
        color: p.line2Color, opacity: l2, transform: `translateY(${57 * (1 - l2)}px)`}}>{p.line2}</div>
    </AbsoluteFill>
  );
};
