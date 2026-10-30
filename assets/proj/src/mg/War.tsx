// War（＝TornReveal）＝破れた形のマスクで絵が隅から広がる。51 の parts/Extra.tsx War の汎用版（51 は白黒の戦場の写真が右下から）
// 何をする：中心 c（画面の隅など）から扇形の多角形を広げ、その形で絵を切り抜く。縁は乱数でぎざぎざ（onN コマごとに形を替える＝2コマ打ち）
// props：
//   f・img・e＝{"<コマ>": 広がり 0〜1}（手本の毎コマの見えとる面積から逆算した表）か steps＝[[コマ, 広がり]…]
//   c([1650,1080])・a([0.55,1.6]＝角度の範囲 ×π・0＝右・0.5＝下)・r0(250)・rv(1500)＝半径＝(r0+rv·e)・squash([1.1,0.85])＝横・縦の伸び
//   jitter([0.82,0.25])＝半径 ×(j0 + j1·乱数)・pts(40)・onN(2)・close（多角形を閉じる点・既定＝画面の右下 [W,H]）
//   filter（51＝'blur(7px) brightness(1.45) contrast(0.7)'）・seed
// 51 で効いた数字：広がりを「面積から逆算した表」にした（7%→20%→33%→48%→54%→59%→66%・2コマ打ちで後から速くなる）＝43秒 SSIM 0.591→0.680・ΔE 6.4→1.6
// 測る道具：mg_measure.py area <手本> f0 f1 --far <下の地の色>＝絵の見えとる割合を毎コマ → うちの書き出しも同じに測って、e の表を1歩ずつ寄せる（2〜3回で合う）
//   手本を 1コマずつ並べて広がる隅と角度（c・a）を目で決める
import React from 'react';
import {Img, random, staticFile, useVideoConfig} from 'remotion';
import {onN, stepAt} from './common';

export const War: React.FC<{f: number; img: string; e?: Record<string, number>; steps?: [number, number][]; c?: [number, number]; a?: [number, number]; r0?: number; rv?: number;
  squash?: [number, number]; jitter?: [number, number]; pts?: number; onN?: number; close?: [number, number]; filter?: string; seed?: string}> = (P) => {
  const {width: W, height: H} = useVideoConfig();
  const {f} = P;
  const e = (P.e ? P.e[String(f)] : stepAt(P.steps, f)) ?? 0;
  if (e <= 0) return null;
  const [cx, cy] = P.c ?? [1650, 1080];
  const [a0, a1] = P.a ?? [0.55, 1.6];
  const [sx, sy] = P.squash ?? [1.1, 0.85];
  const [j0, j1] = P.jitter ?? [0.82, 0.25];
  const n = P.pts ?? 40; const st = onN(f, P.onN ?? 2); const seed = P.seed ?? 'wr';
  const pts: string[] = [];
  for (let i = 0; i <= n; i++) {
    const ang = Math.PI * (a0 + (a1 - a0) * (i / n));
    const r = ((P.r0 ?? 250) + (P.rv ?? 1500) * e) * (j0 + j1 * random(`${seed}${i}_${st}`));
    pts.push(`${cx + Math.cos(ang) * r * sx}px ${cy + Math.sin(ang) * r * sy}px`);
  }
  const close = P.close ?? [W, H];
  pts.push(`${close[0]}px ${close[1]}px`);
  return <Img src={staticFile(P.img)} style={{position: 'absolute', inset: 0, width: W, height: H, clipPath: `polygon(${pts.join(',')})`, filter: P.filter}} />;
};
export const TornReveal = War;
