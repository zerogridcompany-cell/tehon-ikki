// 平たい物（札・紙・葉・カード・写真など）が回る・はじける・降る。51 の parts/Money.tsx（Bill・Burst・FallBills・Rain2・Rain3）と Scenes.tsx Rain の汎用版
// 🔴 51 ではお札やったが、絵（src）と縦横比（ratio）を替えれば何でも。本物の紙幣そっくりは作らん（架空の札を Codex で）
// 乱数は全部 random("種")＝毎回同じ（書き出しをまたいでも同じ所に出る）。seed を替えると別の散らばり
//
// Bill（＝Flat）：1枚。3D の回り（rotateX＝ひらひら裏返る・rotateY・rotateZ）＋ぶれ＋影。裏返る時は暗く（明るさ 0.55＋0.45·|cos rx|）
//   props：x,y（真ん中）・w・ratio（高さ÷幅）・src・rx,ry,rz（度）・blur・op・shadow・perspective(1400)
// Burst：真ん中からはじけて奥→手前へ（z が縮むと大きく・速く）。51 A1＝140枚・z 6〜16・横切る1枚（cross）
//   props：f0・n(140)・cx,cy・spread[横,縦](1.25,0.85)・z[6,16]・zv[1.1,2.0]（コマごとの近づき）・r0(260)・rv(120)・w0(900)・g(1.5)・maxBlur(10)・seed・cross{f0,f1,from,to,w,rz,rx,blur}
// FallBills：上から落ちる。items＝[始まりのコマ, x, 幅, 横 px/コマ, 落ち px/コマ, 回りの種]
//   props：items・y0(-260)・g(0.25 px/コマ²)・flutter(1)・blur(2)・shadow。ひらひら＝rotateX 50·sin(0.35t)・横ゆれ 60·sin(0.22t)（t＝コマ・51 実測）
// Rain：黒地などに大量に散って漂い落ちる（破裂して減速）。51 C1＝340枚・中心 (880,450)
//   props：f0・n・cx,cy・ks＝{"<コマ>":[広がり k, 大きさ s]}（手本の見えとる面積から逆算した表）。無ければ k＝1−e^(−t/tau)・s＝1
//          R[120,1250]・w[60,260]・vy[1,2.5]・tau(7)・seed
// RainRects：手本の札を毎コマ「塊」で測った四角（中心・幅・高さ・角度・明るさ・面積）に、うちの絵を置く（画素は使わん）
//   props：rects＝{"<コマ>":[[cx,cy,w,h,deg,lum,area]…]}・src・lum（絵の平均の明るさ・51＝165）・k(1.06)
// Scatter：画面いっぱいに散らして重力で落とす（51 の Scenes.tsx Rain＝110枚）
//
// 51 で効いた数字：
//   Rain（面積から逆算した k,s の表）＝82.63秒の切り替えが合った・ΔE 1.7→1.2・83秒の動き 55→44（手本 45）
//   RainRects（塊の四角に置く）＝札の雨 SSIM 0.31→0.50。🔴 枚数を増やすと動きは合うが SSIM が下がる＝動きの量は大きさで合わせる
//   Burst は SSIM 0.37 のまま（札が重なって大きな塊になる＝四角では測れん）。1枚ずつ点で追う道具は未作
// 測る道具：
//   見えとる面積と広がり＝mg_measure.py area <手本> f0 f1 [--thr 40]（Y>thr の割合と x の 5〜95% 幅）→ うちも同じに測って k,s を1歩ずつ寄せる（51/tools/rain_fit.py の考え）
//   塊の四角＝mg_measure.py rects <手本> f0 f1 [--min 300] [--paper r,g,b] → {"<コマ>":[[cx,cy,w,h,deg,lum,area]…]} をそのまま rects に
//   落ちる札＝点の追跡は札がぶれすぎて取れん（51）＝手本を 10fps で並べて目で置く（始まりのコマ・x・幅）
import React from 'react';
import {Img, random, staticFile} from 'remotion';
import {lerp} from './common';

type BillP = {x: number; y: number; w: number; ratio?: number; src: string; rx?: number; ry?: number; rz?: number; blur?: number; op?: number; shadow?: boolean; perspective?: number; filter?: string};
export const Bill: React.FC<BillP> = ({x, y, w, ratio = 0.4, src, rx = 0, ry = 0, rz = 0, blur = 0, op = 1, shadow, perspective = 1400, filter}) => {
  const h = w * ratio;
  const shade = 0.55 + 0.45 * Math.abs(Math.cos((rx * Math.PI) / 180));
  return (
    <div style={{position: 'absolute', left: x - w / 2, top: y - h / 2, width: w, height: h, transform: `perspective(${perspective}px) rotateZ(${rz}deg) rotateY(${ry}deg) rotateX(${rx}deg)`, opacity: op,
      filter: `${blur > 0.4 ? `blur(${blur}px) ` : ''}brightness(${shade})${shadow ? ' drop-shadow(0 18px 14px rgba(0,0,0,0.28))' : ''}${filter ? ' ' + filter : ''}`}}>
      <Img src={staticFile(src)} style={{width: '100%', height: '100%'}} />
    </div>
  );
};
export const Flat = Bill;

export const Burst: React.FC<{f: number; f0: number; src: string; ratio?: number; n?: number; cx?: number; cy?: number; spread?: [number, number]; z?: [number, number]; zv?: [number, number];
  r0?: number; rv?: number; w0?: number; g?: number; maxBlur?: number; seed?: string; W?: number; H?: number;
  cross?: {f0: number; f1: number; from: [number, number]; to: [number, number]; w: number; rz?: [number, number]; rx?: number; blur?: number}}> = (P) => {
  const t = P.f - P.f0; if (t < 0) return null;
  const {src, ratio, n = 140, cx = 960, cy = 520, spread = [1.25, 0.85], z = [6, 16], zv = [1.1, 2.0], r0 = 260, rv = 120, w0 = 900, g = 1.5, maxBlur = 10, seed = 'b', W = 1920, H = 1080} = P;
  const out: React.ReactNode[] = [];
  for (let i = 0; i < n; i++) {
    const a = random(`${seed}a${i}`) * Math.PI * 2; const sp = 0.6 + random(`${seed}s${i}`) * 1.2;
    const z0 = z[0] + random(`${seed}z${i}`) * (z[1] - z[0]); const zz = Math.max(0.35, z0 - t * (zv[0] + random(`${seed}v${i}`) * (zv[1] - zv[0])));
    const r = ((r0 + t * rv * sp) / zz) * 6;
    const x = cx + Math.cos(a) * r * spread[0]; const y = cy + Math.sin(a) * r * spread[1] + t * t * g;
    const w = w0 / zz;
    if (x < -w || x > W + w || y < -w || y > H + w) continue;
    out.push(<Bill key={i} src={src} ratio={ratio} x={x} y={y} w={w} rx={random(`${seed}x${i}`) * 360 + t * 40 * (random(`${seed}w${i}`) - 0.5)} ry={(random(`${seed}y${i}`) - 0.5) * 70} rz={random(`${seed}r${i}`) * 360 + t * 25} blur={Math.min(maxBlur, (t * sp * 3) / zz)} />);
  }
  const c = P.cross;
  if (c && P.f >= c.f0 && P.f < c.f1) { const p = (P.f - c.f0) / (c.f1 - c.f0); out.push(<Bill key="cross" src={src} ratio={ratio} x={lerp(c.from[0], c.to[0], p)} y={lerp(c.from[1], c.to[1], p)} w={c.w} rz={lerp(c.rz?.[0] ?? -12, c.rz?.[1] ?? -2, p)} rx={c.rx ?? 20} blur={c.blur ?? 6} />); }
  return <>{out}</>;
};

export type Fall = [number, number, number, number, number, number];
export const FallBills: React.FC<{f: number; items: Fall[]; src: string; ratio?: number; y0?: number; g?: number; flutter?: number; blur?: number; shadow?: boolean; H?: number}> = ({f, items, src, ratio, y0 = -260, g = 0.25, flutter = 1, blur = 2, shadow, H = 1080}) => (
  <>
    {items.map(([s, x, w, vx, vy, k], i) => {
      const t = f - s; if (t < 0) return null;
      const y = y0 + vy * t + g * t * t; if (y > H + w) return null;
      const sw = Math.sin(t * 0.22 + k) * 60 * flutter;
      return <Bill key={i} src={src} ratio={ratio} x={x + vx * t + sw} y={y} w={w} rx={flutter ? 50 * Math.sin(t * 0.35 + k * 2) + t * 6 : 0} ry={20 * Math.sin(t * 0.2 + k)} rz={k * 40 + t * (k % 2 ? 3 : -3)} blur={blur + Math.abs(vy) / 40} shadow={shadow} />;
    })}
  </>
);

export const Rain: React.FC<{f: number; f0: number; src: string; ratio?: number; n?: number; cx?: number; cy?: number; ks?: Record<string, [number, number]>; R?: [number, number]; w?: [number, number];
  vy?: [number, number]; tau?: number; seed?: string; W?: number; H?: number}> = (P) => {
  const t = P.f - P.f0; if (t < 0 && !P.ks) return null;
  const {src, ratio, n = 340, cx = 880, cy = 450, R = [120, 1250], w = [60, 260], vy = [1, 2.5], tau = 7, seed = 'r', W = 1920, H = 1080} = P;
  let k: number, s: number;
  if (P.ks) { const v = P.ks[String(P.f)]; if (!v) return null; [k, s] = v; } else { k = 1 - Math.exp(-t / tau); s = 1; }
  const tt = Math.max(0, t); const kr = 1 - Math.exp(-tt / 10);
  return (
    <>
      {Array.from({length: n}).map((_, i) => {
        const a = random(`${seed}a${i}`) * Math.PI * 2; const r = R[0] + Math.sqrt(random(`${seed}r${i}`)) * (R[1] - R[0]);
        const x = cx + Math.cos(a) * r * k * 1.15 + Math.sin(tt * 0.15 + i) * 6;
        const y = cy + Math.sin(a) * r * k * 0.8 + (vy[0] + random(`${seed}v${i}`) * (vy[1] - vy[0])) * tt;
        const ww = (w[0] + random(`${seed}w${i}`) * random(`${seed}w2${i}`) * (w[1] - w[0])) * (0.55 + 0.45 * k) * s;
        if (y > H + 120 || y < -200 || x < -250 || x > W + 250) return null;
        const spin = (kr * 12 + tt * 0.15);
        return <Bill key={i} src={src} ratio={ratio} x={x} y={y} w={ww} rx={random(`${seed}qa${i}`) * 360 + spin * (random(`${seed}qb${i}`) - 0.5) * 24} ry={(random(`${seed}qc${i}`) - 0.5) * 80} rz={random(`${seed}qd${i}`) * 360 + spin * (random(`${seed}qe${i}`) - 0.5) * 10} blur={1} />;
      })}
    </>
  );
};

export const RainRects: React.FC<{f: number; rects: Record<string, number[][]>; src: string; lum?: number; k?: number}> = ({f, rects, src, lum = 165, k = 1.06}) => {
  const rs = rects[String(f)]; if (!rs) return null;
  return (
    <>
      {rs.map((r, i) => {
        const [cx, cy, w, h0, a, l, area] = r;
        const h = area ? Math.max(h0 * 0.25, Math.min(h0, (1.15 * area) / Math.max(1, w))) : h0; // 丸まった物＝四角いっぱいやない＝塊の面積（ぼけの縁ぶん ×1.15）を保つ高さ
        return <div key={i} style={{position: 'absolute', left: cx - w / 2, top: cy - h / 2, width: w, height: h, transform: `rotate(${a}deg)`, filter: `brightness(${Math.min(1.7, (k * (l ?? lum)) / lum)}) saturate(0.8)`}}><Img src={staticFile(src)} style={{width: '100%', height: '100%'}} /></div>;
      })}
    </>
  );
};

export const Scatter: React.FC<{f: number; f0: number; src: string; ratio?: number; n?: number; seed?: string; W?: number; H?: number; tiles?: number; border?: string; fps?: number}> = ({f, f0, src, ratio = 96 / 220, n = 110, seed = 'sc', W = 1920, H = 1080, tiles = 4, border, fps = 30}) => {
  const tt = (f - f0) / fps; if (tt < 0) return null;
  return (
    <>
      {Array.from({length: n}).map((_, i) => {
        const x = -150 + random(`${seed}x${i}`) * (W + 300) + (random(`${seed}dx${i}`) - 0.5) * 500 * tt;
        const y = -250 + random(`${seed}y${i}`) * (H + 420) + (150 + random(`${seed}v${i}`) * 450) * tt + 250 * tt * tt;
        const rot = random(`${seed}r${i}`) * 360 + tt * (random(`${seed}w${i}`) - 0.5) * 700;
        const s = 0.3 + random(`${seed}s${i}`) * 0.5; const w = 220 * s, h = w * ratio;
        return <div key={i} style={{position: 'absolute', left: x - w / 2, top: y - h / 2, width: w, height: h, backgroundImage: `url(${staticFile(src)})`, backgroundSize: tiles > 1 ? `${tiles * 100}% ${tiles * 100}%` : 'cover', backgroundPosition: `${(i * 37) % 100}% ${(i * 53) % 100}%`, border, transform: `rotate(${rot}deg) scaleY(${Math.cos(tt * 8 + i)})`}} />;
      })}
    </>
  );
};
