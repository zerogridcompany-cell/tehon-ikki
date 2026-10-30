import React from 'react';
import {useCurrentFrame} from 'remotion';
import HUD from './hud.json';
// 追跡の飾り（r2 23〜25）＝手本のコマごとに測った 赤い線の切れ端・緑の点・座標の字・白い点線（tools/hud_measure.py）。手本の画素は使わん
type Fr = {boxes: number[][]; dots: number[][]; texts: any[][]; dash: number[][]; border: boolean};
const D = HUD as Record<string, Fr>;
export const Hud: React.FC = () => {
  const f = useCurrentFrame();
  const h = D[String(f)];
  if (!h) return null;
  return (
    <svg width={1280} height={720} style={{position: 'absolute', inset: 0, filter: 'blur(0.45px)'}}>
      {h.border && <rect x={1} y={1} width={1278} height={718} fill="none" stroke="#e23a4f" strokeWidth={2} />}
      {h.boxes.map((s, i) => <line key={'b' + i} x1={s[0]} y1={s[1]} x2={s[2]} y2={s[3]} stroke="#e23a4f" strokeWidth={2.2} />)}
      {h.dash.map((p, i) => <rect key={'d' + i} x={p[0] - 0.8} y={p[1] - 0.8} width={1.8} height={1.8} fill="#f0eaf4" />)}
      {h.dots.map((p, i) => <circle key={'g' + i} cx={p[0]} cy={p[1]} r={4.2} fill="#28ec28" />)}
      {h.texts.map((t, i) => (
        <text key={'t' + i} x={t[0]} y={t[1]} fill="#efeaf4" style={{fontFamily: 'R2Sans', fontWeight: 500, fontSize: Math.max(18, Math.min(25, t[6]))}}>{t[4]}</text>
      ))}
    </svg>
  );
};
