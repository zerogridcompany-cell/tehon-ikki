import React from 'react';
import {AbsoluteFill, Img, continueRender, delayRender, staticFile, useCurrentFrame} from 'remotion';
import GREEN from './green.json';
import GRID from './grid.json';
import GRAIN from './grain.json';

// 緑の技術図面の場面（30〜36・39〜41）。
// 一枚絵＝Codex が手本のコマを下敷きに描き直した絵（mg/green/<id>/plate.png）→ tools/green_fit.py で色を当てた絵（public/green/<id>.png）。
// 置き方＝手本の1コマずつに ECC で合わせた 2x3 行列（絵の画素→画面の画素）・ぼかし＝絵の画素での σ。
// 数字表（31・36 の頭）＝Chakra Petch Bold を1字ずつ置く。光＝Python で当てた σ ごとの色の重み（mg/green/grid/fit_grid.py）をそのまま SVG で足す。
// seq＝動きの写し（tools/flow_tx.py）で曲げたコマ。その絵は public/fx/<id>/<f>.jpg＝画面の大きさ・ぼかし込み＝変形なしで出す
type Plate = {f0: number; f1: number; w: number; h: number; blur: number; M: Record<string, number[]>; seq?: number[]};
// 粒＝手本のコマごとの細かい揺れから、うちに足りん分（mg/grain_need.json・上限3）を、SVG のノイズ（種＝コマ番号）で足す。強さの換算 GRAIN_K は実測
const GRAIN_K = 0.038;
type Glyph = {ch: string; x: number; y: number; fs: number; sx: number};
type W3 = Record<'R' | 'G' | 'B', number[]>;
type GridT = {glyphs: Glyph[]; sig: number[]; w: W3; shots: {f0: number; f1: number; m: number[]; sig?: number[]; w?: W3}[]};

// 書体を読み終わるまで描かん（読む前に描くと別の太い書体に化ける＝motion-cm「書体の罠」）
const fontH = delayRender('R2Grid');
new FontFace('R2Grid', `url(${staticFile('fonts/ChakraPetch-Bold.ttf')})`, {weight: '700'}).load()
  .then((ff) => { (document.fonts as any).add(ff); continueRender(fontH); }).catch(() => continueRender(fontH));
const G = GRID as GridT;

const Glyphs: React.FC<{m: number[]; fill: string}> = ({m, fill}) => (
  <g transform={`matrix(${m.join(' ')})`}>
    {G.glyphs.map((g, i) => (
      <text key={i} x={0} y={0} fill={fill} transform={`translate(${g.x} ${g.y}) scale(${g.sx} 1)`}
        style={{fontFamily: 'R2Grid', fontWeight: 700, fontSize: g.fs}}>
        {g.ch}
      </text>
    ))}
  </g>
);

// 光＝σ ごとに字を1枚ずつ（その σ の色の重みで塗ってぼかす）→ 足し算で重ねる（Python の当てと同じ式）
const GridGlow: React.FC<{m: number[]; maskOnly?: boolean; sig?: number[]; w?: W3}> = ({m, maskOnly, sig = G.sig, w = G.w}) => {
  const n = sig.length;
  if (maskOnly) return <svg width={1280} height={720} style={{position: 'absolute', inset: 0}}><Glyphs m={m} fill="#fff" /></svg>;
  return (
    <AbsoluteFill style={{background: `rgb(${w.R[n]},${w.G[n]},${w.B[n]})`, isolation: 'isolate'}}>
      {sig.map((sg, j) => {
        if (w.R[j] + w.G[j] + w.B[j] < 0.5) return null;
        return (
          <svg key={j} width={1280} height={720}
            style={{position: 'absolute', inset: 0, mixBlendMode: 'plus-lighter', filter: sg ? `blur(${sg * m[0]}px)` : undefined}}>
            <Glyphs m={m} fill={`rgb(${w.R[j]},${w.G[j]},${w.B[j]})`} />
          </svg>
        );
      })}
    </AbsoluteFill>
  );
};

export const GREEN_RANGES: [number, number][] = [
  ...Object.values(GREEN as Record<string, Plate>).map((p) => [p.f0, p.f1] as [number, number]),
  ...G.shots.map((s) => [s.f0, s.f1] as [number, number]),
];

export const Green: React.FC = () => {
  const f = useCurrentFrame();
  const shot = G.shots.find((s) => f >= s.f0 && f <= s.f1);
  const entry = Object.entries(GREEN as Record<string, Plate>).find(([, p]) => f >= p.f0 && f <= p.f1);
  if (!shot && !entry) return null;
  return (
    <AbsoluteFill style={{backgroundColor: '#000'}}>
      {shot ? <GridGlow m={shot.m} sig={shot.sig} w={shot.w} /> : null}
      {entry ? (() => {
        const [id, p] = entry;
        const M = p.M[String(f)];
        const ga = Math.min(3, (GRAIN as Record<string, number>)[id] ?? 0) * GRAIN_K;
        return (
          <>
          {ga > 0 ? (
            <svg width={0} height={0} style={{position: 'absolute'}}>
              <filter id={`gr${f}`} x="0" y="0" width="100%" height="100%" colorInterpolationFilters="sRGB">
                <feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves={1} seed={f} result="n" />
                <feColorMatrix in="n" type="matrix" values="1 0 0 0 0  1 0 0 0 0  1 0 0 0 0  0 0 0 0 1" result="g" />
                <feComposite in="SourceGraphic" in2="g" operator="arithmetic" k1={0} k2={1} k3={ga} k4={-ga * 0.5} />
              </filter>
            </svg>
          ) : null}
          {p.seq?.includes(f) ? (
            <Img src={staticFile(`fx/${id}/${f}.jpg`)}
              style={{position: 'absolute', left: 0, top: 0, width: 1280, height: 720, filter: ga > 0 ? `url(#gr${f})` : undefined}} />
          ) : (
          <Img src={staticFile(`green/${id}.png`)}
            style={{position: 'absolute', left: 0, top: 0, width: p.w, height: p.h, transformOrigin: '0 0',
              transform: `matrix(${M[0]}, ${M[3]}, ${M[1]}, ${M[4]}, ${M[2]}, ${M[5]})`,
              filter: [p.blur ? `blur(${p.blur}px)` : '', ga > 0 ? `url(#gr${f})` : ''].join(' ').trim() || undefined}} />
          )}
          </>
        );
      })() : null}
    </AbsoluteFill>
  );
};

// 当て直し用：字だけ（白・光なし）。mg/green/grid/fit_grid_chrome.py が読む
export const GridMask: React.FC<{k?: number}> = ({k = 0}) => <AbsoluteFill style={{backgroundColor: '#000'}}><GridGlow m={G.shots[k].m} maskOnly /></AbsoluteFill>;
