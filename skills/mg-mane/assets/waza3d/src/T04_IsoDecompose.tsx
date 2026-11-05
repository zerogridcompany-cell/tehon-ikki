// T04 IsoDecompose（手札 R1_03・道 A＝CSS 3D のアイソメ）
// 等角に寝かせた調べの表を光の帯が走査 → 読めた所が色の板として持ち上がり → 右上へ 4 枚の札に分かれる。
// カメラは 1 軸（ゆっくり寄る）。板は ease out で 6 コマずつ遅れて着地・影は高さでぼける。
import React from 'react';
import {AbsoluteFill, Img, staticFile, useCurrentFrame} from 'remotion';
import {E, FONT, GRAIN, clamp01, lerp, tw, breathe} from './lib';

export type T04Region = {x: number; y: number; w: number; h: number; color: string; label: string; value: string};
export type T04Props = {accent: string; title: string; rows: {name: string; img: string; price: string; sold: string; rating: string}[]; regions: T04Region[]; bg: string};
const D = (c: string) => `zg/daruma_${c}.png`;
export const t04Defaults: T04Props = {
  accent: '#5268e4',
  title: 'Trending in Japan · this week',
  rows: [
    {name: 'Daruma · Red', img: D('red'), price: '¥2,980', sold: '4,812', rating: '4.9'},
    {name: 'Daruma · Gold', img: D('yellow'), price: '¥3,480', sold: '3,105', rating: '4.8'},
    {name: 'Daruma · Blue', img: D('blue'), price: '¥2,980', sold: '2,240', rating: '4.7'},
    {name: 'Daruma · Brown', img: D('brown'), price: '¥2,480', sold: '1,960', rating: '4.8'},
    {name: 'Daruma · Mini set', img: D('red'), price: '¥1,980', sold: '1,402', rating: '4.6'},
  ],
  // 表の上の領域（表の座標 px）
  regions: [
    {x: 24, y: 84, w: 300, h: 420, color: '#5268e4', label: 'Product', value: '5 found'},
    {x: 336, y: 84, w: 150, h: 420, color: '#1f9d7a', label: 'Price', value: '¥2,780 avg'},
    {x: 498, y: 84, w: 150, h: 420, color: '#d9488f', label: 'Sold / week', value: '13.5k'},
    {x: 660, y: 84, w: 136, h: 420, color: '#8a5cf0', label: 'Reviews', value: '4.8 ★'},
  ],
  bg: '#cfdff6',
};
const src = (s: string) => (s.startsWith('http') ? s : staticFile(s));
const DW = 820, DH = 540;

const Doc: React.FC<{p: T04Props}> = ({p}) => (
  <div style={{position: 'absolute', inset: 0, background: '#f8fcfd', borderRadius: 14, fontFamily: FONT, overflow: 'hidden', boxShadow: '0 0 0 1px #e8e7ed'}}>
    <div style={{position: 'absolute', left: 24, top: 22, fontSize: 20, fontWeight: 600, color: '#040506'}}>{p.title}</div>
    <div style={{position: 'absolute', right: 24, top: 24, fontSize: 12, fontWeight: 600, color: p.accent, background: `${p.accent}14`, padding: '4px 10px', borderRadius: 6}}>Research</div>
    <div style={{position: 'absolute', left: 24, right: 24, top: 70, height: 1, background: '#e8e7ed'}} />
    {['Product', 'Price', 'Sold / week', 'Rating'].map((h, i) => (
      <div key={h} style={{position: 'absolute', top: 92, left: [40, 352, 514, 676][i], fontSize: 13, fontWeight: 500, color: '#8b93a1'}}>{h}</div>
    ))}
    {p.rows.map((r, i) => (
      <div key={i} style={{position: 'absolute', left: 24, right: 24, top: 124 + i * 76, height: 76, borderTop: i ? '1px solid #eceef2' : 'none', display: 'flex', alignItems: 'center', fontSize: 15, color: '#3a3f4b'}}>
        <div style={{width: 312, display: 'flex', alignItems: 'center', gap: 12, paddingLeft: 14}}>
          <div style={{width: 44, height: 44, borderRadius: 10, background: '#f1f3f6', display: 'flex', alignItems: 'center', justifyContent: 'center'}}><Img src={src(r.img)} style={{height: 34}} /></div>
          <span style={{fontWeight: 500, color: '#040506'}}>{r.name}</span>
        </div>
        <div style={{width: 162, paddingLeft: 4, fontVariantNumeric: 'tabular-nums'}}>{r.price}</div>
        <div style={{width: 162, paddingLeft: 4, fontVariantNumeric: 'tabular-nums'}}>{r.sold}</div>
        <div style={{paddingLeft: 4}}>{r.rating} <span style={{color: '#e8a33c'}}>★</span></div>
      </div>
    ))}
  </div>
);

export const T04_IsoDecompose: React.FC<Partial<T04Props>> = (props) => {
  const p = {...t04Defaults, ...props};
  const f = useCurrentFrame();
  const cam = tw(f, -24, 104, E.linear); // カメラの引き（一定の速さ・止まらん）
  const camE = tw(f, -24, 104, E.inout);
  const scan = tw(f, -8, 30, E.inout); // 走査 0→1
  const scanX = lerp(-40, DW + 40, scan);
  return (
    <AbsoluteFill style={{background: p.bg, overflow: 'hidden'}}>
      {/* 淡い方眼＋上から光 */}
      <AbsoluteFill style={{backgroundImage: 'linear-gradient(rgba(255,255,255,.35) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.35) 1px, transparent 1px)', backgroundSize: '48px 48px',
        transform: `scale(${lerp(1, 1.06, cam)})`}} />
      <AbsoluteFill style={{background: 'radial-gradient(circle 900px at 40% 20%, rgba(255,255,255,.55) 0, rgba(255,255,255,.15) 45%, transparent 100%)'}} />
      <AbsoluteFill style={{perspective: 3200, perspectiveOrigin: '50% 40%'}}>
        <div style={{position: 'absolute', left: 960 - DW / 2 - 330, top: 640 - DH / 2, width: DW, height: DH, transformStyle: 'preserve-3d',
          transform: `translate(${lerp(-90, 10, camE)}px, ${lerp(150, 70, camE)}px) scale(${lerp(1.8, 1.45, camE)}) rotateX(56deg) rotateZ(${lerp(-50, -34, cam)}deg)`}}>
          {/* 表の落ち影（床に） */}
          <div style={{position: 'absolute', inset: 0, borderRadius: 14, background: 'rgba(40,60,110,.28)', filter: 'blur(22px)', transform: 'translate3d(10px,18px,-2px)'}} />
          <Doc p={p} />
          {/* 走査で読めた所に色が乗る（帯の通った分だけ） */}
          {p.regions.map((r, i) => {
            const cov = clamp01((scanX - r.x) / r.w);
            return <div key={i} style={{position: 'absolute', left: r.x, top: r.y, width: r.w * cov, height: r.h, background: `${r.color}24`, borderRadius: 8, transform: 'translateZ(1px)'}} />;
          })}
          {/* 走査の帯（光の線＋尾） */}
          <div style={{position: 'absolute', left: scanX - 120, top: -10, width: 120, height: DH + 20, transform: 'translateZ(2px)', opacity: 1 - tw(f, 28, 36, E.in),
            background: `linear-gradient(90deg, ${p.accent}00 0%, ${p.accent}22 70%, ${p.accent}88 97%, #ffffff 100%)`}} />
          <div style={{position: 'absolute', left: scanX - 2, top: -16, width: 3, height: DH + 32, background: '#fff', boxShadow: `0 0 12px 2px ${p.accent}, 0 0 40px 6px ${p.accent}88`, transform: 'translateZ(3px)', opacity: 1 - tw(f, 28, 36, E.in)}} />
          {/* 持ち上がる板 → 右上の札へ（6 コマずつ遅れて・ease out で着地） */}
          {p.regions.map((r, i) => {
            const k = tw(f, 26 + i * 5, 54 + i * 5, E.out);
            const m = tw(f, 32 + i * 5, 66 + i * 5, E.out);
            const z = lerp(0, 200 + i * 30, k) + 0;
            const tx = lerp(0, 700 - r.x + i * 30, m), ty = lerp(0, -150 + i * 205 - r.y + 84, m);
            const w = lerp(r.w, 308, m), h = lerp(r.h, 134, m);
            const bob = breathe(f, 10, 60, i * 1.1) * m;
            const lab = tw(f, 50 + i * 5, 66 + i * 5, E.out);
            return (
              <React.Fragment key={i}>
                {/* 影（高いほどぼけて薄い） */}
                <div style={{position: 'absolute', left: r.x + tx, top: r.y + ty, width: w, height: h, borderRadius: 10, background: 'rgba(30,50,110,.35)', filter: `blur(${4 + z * 0.12}px)`,
                  opacity: k * lerp(0.9, 0.45, z / 280), transform: `translate3d(${z * 0.18}px, ${z * 0.28}px, 2px)`}} />
                {/* つなぎの線（床の上の点線） */}
                {(() => { const x0 = r.x + r.w / 2, y0 = r.y + 30, x1 = r.x + tx + 30, y1 = r.y + ty + h - 14; const L = Math.hypot(x1 - x0, y1 - y0) * m;
                  const dot = (((f - 32 - i * 5) / 20) % 1 + 1) % 1; const glowS = {background: `linear-gradient(90deg, ${r.color}44, ${r.color}ee)`, boxShadow: `0 0 6px ${r.color}, 0 0 18px ${r.color}99`};
                  return (<>
                  {/* 床の上の光る線（領域→札の足元） */}
                  <div style={{position: 'absolute', left: x0, top: y0, width: L, height: 3, borderRadius: 2, transformOrigin: '0 50%', opacity: m > 0.02 ? 1 : 0, transform: `translateZ(2px) rotate(${Math.atan2(y1 - y0, x1 - x0)}rad)`, ...glowS}}>
                    <div style={{position: 'absolute', left: `${dot * 100}%`, top: -3, width: 9, height: 9, borderRadius: 5, background: '#fff', boxShadow: `0 0 10px 3px ${r.color}`, opacity: f > 36 + i * 5 ? 1 : 0}} />
                  </div>
                  {/* 足元から札へ立つ光の柱 */}
                  <div style={{position: 'absolute', left: x0 + (x1 - x0) * m, top: y0 + (y1 - y0) * m, width: 3, height: z + bob, transformOrigin: '50% 0', opacity: m > 0.6 ? (m - 0.6) / 0.4 : 0,
                    transform: 'translateZ(2px) rotateX(90deg)', background: `linear-gradient(180deg, ${r.color}ee, ${r.color}55)`, boxShadow: `0 0 8px ${r.color}`}} />
                  </>); })()}
                <div style={{position: 'absolute', left: r.x + tx, top: r.y + ty, width: w, height: h, borderRadius: 10, transform: `translateZ(${z + bob}px)`, opacity: Math.min(1, k * 5),
                  background: `linear-gradient(160deg, ${r.color}${Math.round(lerp(0x55, 0xee, m)).toString(16)}, ${r.color}${Math.round(lerp(0x30, 0xc8, m)).toString(16)})`, backdropFilter: 'blur(2px)', boxShadow: `inset 0 1.5px 0 rgba(255,255,255,.55), 0 0 0 1px ${r.color}`, fontFamily: FONT, color: '#fff', overflow: 'hidden'}}>
                  <div style={{position: 'absolute', left: 24, top: 18, fontSize: 24, fontWeight: 600, opacity: 0.92 * lab}}>{r.label}</div>
                  <div style={{position: 'absolute', left: 24, top: 52, fontSize: 48, fontWeight: 700, letterSpacing: '-0.015em', opacity: lab, transform: `translateY(${lerp(12, 0, lab)}px)`}}>{r.value}</div>
                </div>
              </React.Fragment>
            );
          })}
        </div>
      </AbsoluteFill>
      <AbsoluteFill style={{backgroundImage: GRAIN, opacity: 0.035, mixBlendMode: 'overlay'}} />
    </AbsoluteFill>
  );
};
