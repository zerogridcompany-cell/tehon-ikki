// Boil・Jitter・boilState＝紙のしわ・線の「揺れの段」（line boil）。51 の parts/Money.tsx Boil・boilJitter の汎用版
// 何をする：紙の上のしわの影を数枚（既定4枚）用意し、手本の「替わるコマ」の表で入れ替えて画面全体に乗算する。替わる時に絵ごと ±1px ずれる（Jitter）
//   手本の手描き・紙のコラージュは、止まって見える所でもしわと縁が数コマごとにちらちら替わる＝これが無いと「止まった絵」に見える
// props（Boil）：
//   f・table＝{"<コマ>": 0..n-1}（手本の四隅から読んだ替わり）か every（n コマごとに次へ・表が無い時）
//   imgs?   しわの影の絵（乗算用・public の道）。無ければ SVG の feTurbulence（種＝段）で低い周波数のまだらを作る
//   op(0.7)・blend('multiply')・freq(0.012)・amp（まだらの濃さ 0〜1・0.10）
// Jitter：children を段ごとに ±amp px ずらす（random("jx"+段)）。amp 1＝51
// 51 で効いた数字：しわの乗算の強さ＝四隅の「替わるコマの差」を手本と比べて op 1→0.7（差 2.06→1.65・手本 1.66）・ΔE 1.0→0.9
//   替わりの間は手本の中央値で 2〜3コマ（mg_measure.py boil の出力の「間のコマ 中央値」を every に）
// 測る道具：mg_measure.py boil <手本> [--f0 --f1]＝四隅（物の無い紙）の前のコマとの差が 0.35〜8 の小さな替わりのコマを拾う→ {"<コマ>":段} の json を table に
//   🔴 字や物が四隅に来る場面は外す（--f0 --f1 で紙の場面だけ）
import React from 'react';
import {Img, random, staticFile, useVideoConfig} from 'remotion';
import {onN} from './common';

export const boilState = (f: number, table?: Record<string, number>, every = 3, n = 4) => (table ? table[String(f)] ?? 0 : Math.floor(onN(f, every) / every) % n);

export const Boil: React.FC<{f: number; table?: Record<string, number>; every?: number; n?: number; imgs?: string[]; op?: number; blend?: string; freq?: number; amp?: number; id?: string}> = ({f, table, every = 3, n, imgs, op = 0.7, blend = 'multiply', freq = 0.012, amp = 0.1, id = 'boil'}) => {
  const {width: W, height: H} = useVideoConfig();
  const nn = n ?? imgs?.length ?? 4;
  const k = boilState(f, table, every, nn);
  if (imgs && imgs.length) return <Img src={staticFile(imgs[k % imgs.length])} style={{position: 'absolute', inset: 0, width: W, height: H, mixBlendMode: blend as any, opacity: op}} />;
  // 絵が無い時：低い周波数のまだら（白〜少し暗い）を段ごとの種で＝乗算で紙のしわの影に見せる
  const lo = 1 - amp;
  return (
    <svg width={W} height={H} style={{position: 'absolute', inset: 0, mixBlendMode: blend as any, opacity: op}}>
      <filter id={`${id}${k}`} x="0" y="0" width="100%" height="100%" colorInterpolationFilters="sRGB">
        <feTurbulence type="fractalNoise" baseFrequency={freq} numOctaves={3} seed={k * 17 + 5} />
        <feColorMatrix type="saturate" values="0" />
        <feComponentTransfer><feFuncR type="linear" slope={amp * 2} intercept={lo} /><feFuncG type="linear" slope={amp * 2} intercept={lo} /><feFuncB type="linear" slope={amp * 2} intercept={lo} /><feFuncA type="linear" slope={0} intercept={1} /></feComponentTransfer>
      </filter>
      <rect x={0} y={0} width={W} height={H} filter={`url(#${id}${k})`} />
    </svg>
  );
};

export const boilJitter = (k: number, amp = 1): [number, number] => [(random(`jx${k}`) - 0.5) * 2 * amp, (random(`jy${k}`) - 0.5) * 2 * amp];
export const Jitter: React.FC<{f: number; table?: Record<string, number>; every?: number; amp?: number; children?: React.ReactNode}> = ({f, table, every = 3, amp = 1, children}) => {
  const [dx, dy] = boilJitter(boilState(f, table, every), amp);
  return <div style={{position: 'absolute', inset: 0, transform: `translate(${dx}px,${dy}px)`}}>{children}</div>;
};
