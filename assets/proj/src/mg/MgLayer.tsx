// MgLayer＝src/mg.json に並べた MG の部品を、そのコマに出す口（Main.tsx から呼ぶ）
// mg.json＝[{ "part": "部品名", "f0": 始まりのコマ, "f1": 終わりのコマ（含む）, "props": {…}, "layer": "under"|"over", "style": {opacity, mixBlendMode, filter}, "id": "名札" }, …]
//   part＝下の PARTS の名前。props＝その部品の props（f は MgLayer が今のコマを入れる）。並びの順に下から重なる
//   layer：'under'＝土台の動画のすぐ上・一枚絵（Green）の下（紙の地 Paper・しわ Boil など）／'over'（既定）＝カードの上・字幕の下
//          'top'＝一番上・場面の色の変換とぼかし（shot_look・cuttune）の外（通知など、くっきりさせたい物）
//   大きい表（毎コマ測った json）は public に置いて "@mg/rain_rects.json" のように "@" で始まる文字で渡す（読み終わるまで delayRender で待つ）
// 🔴 mg.json が [] なら何も描かん＝今までの書き出しと同じ（t51ikki など前の作業はそのまま）
import React, {useEffect, useState} from 'react';
import {AbsoluteFill, continueRender, delayRender, staticFile, useCurrentFrame} from 'remotion';
import {Paper} from './Paper';
import {Chat, Bub} from './Chat';
import {Notif} from './Notif';
import {Static} from './Static';
import {Bill, Burst, FallBills, Rain, RainRects, Scatter} from './Flat';
import {Boil} from './Boil';
import {CrumpleBall} from './CrumpleBall';
import {Scribble} from './Scribble';
import {War} from './War';
import {Swap} from './Swap';
import {CamImg} from './CamImg';

export const PARTS: Record<string, React.FC<any>> = {Paper, Chat, Bub, Notif, Static, Bill, Flat: Bill, Burst, FallBills, Rain, RainRects, Scatter, Boil, CrumpleBall, Scribble, War, TornReveal: War, Swap, CamImg};

export type MgItem = {part: string; f0: number; f1: number; props?: Record<string, any>; layer?: 'under' | 'over' | 'top'; style?: React.CSSProperties; id?: string};

// "@道" の表を読む（1回だけ・全部の部品で共有）
const CACHE: Record<string, any> = {};
const refsOf = (v: any, out: Set<string>) => {
  if (typeof v === 'string' && v.startsWith('@')) out.add(v.slice(1));
  else if (Array.isArray(v)) v.forEach((x) => refsOf(x, out));
  else if (v && typeof v === 'object') Object.values(v).forEach((x) => refsOf(x, out));
};
const resolve = (v: any): any => {
  if (typeof v === 'string' && v.startsWith('@')) return CACHE[v.slice(1)];
  if (Array.isArray(v)) return v.map(resolve);
  if (v && typeof v === 'object' && !React.isValidElement(v)) return Object.fromEntries(Object.entries(v).map(([k, x]) => [k, resolve(x)]));
  return v;
};
const useTables = (items: MgItem[]) => {
  const [ready, setReady] = useState(() => {
    const need = new Set<string>(); items.forEach((it) => refsOf(it.props, need));
    return [...need].every((p) => p in CACHE);
  });
  const [handle] = useState(() => (ready ? null : delayRender('MgLayer tables')));
  useEffect(() => {
    if (ready || handle == null) return;
    const need = new Set<string>(); items.forEach((it) => refsOf(it.props, need));
    Promise.all([...need].filter((p) => !(p in CACHE)).map((p) => fetch(staticFile(p)).then((r) => r.json()).then((j) => { CACHE[p] = j; })))
      .then(() => { setReady(true); continueRender(handle); })
      .catch((e) => { console.error('MgLayer: 表が読めん', e); setReady(true); continueRender(handle); });
  }, [ready, handle, items]);
  return ready;
};

export const MgLayer: React.FC<{items: MgItem[]; layer?: 'under' | 'over' | 'top'}> = ({items, layer = 'over'}) => {
  const f = useCurrentFrame();
  const mine = items.filter((it) => (it.layer ?? 'over') === layer);
  const ready = useTables(mine);
  if (!ready || !mine.length) return null;
  const on = mine.filter((it) => f >= it.f0 && f <= it.f1);
  if (!on.length) return null;
  return (
    <>
      {on.map((it, i) => {
        const C = PARTS[it.part];
        if (!C) { console.warn(`MgLayer: 部品が無い ${it.part}`); return null; }
        return <AbsoluteFill key={it.id ?? `${it.part}_${it.f0}_${i}`} style={it.style}><C {...resolve(it.props ?? {})} f={f} /></AbsoluteFill>;
      })}
    </>
  );
};
