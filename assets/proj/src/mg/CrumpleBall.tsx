// CrumpleBall＝描き分けの絵を段の表で替えて「形が変わる物」を見せる（紙の玉が開く・花が開く・缶がつぶれる…）。51 の parts/Money.tsx CrumpleBall の汎用版
// 何をする：table の行ごとに絵・中心・幅を替える（2コマごと等の段）。間は滑らかにせん（手作りの段の味）。毎コマ少し傾ける（wobble）
// props：
//   f・table＝[[コマ, 絵, 中心x, 中心y, 幅, 高さ÷幅]…]（コマの小さい順）・f1（ここで消える・無ければ最後の行から hold コマ）
//   wobble（[周期のコマ, 度の幅]・既定 [4, 2]＝51 の (f%4)*2−3 度）・shadow（drop-shadow の CSS）
// 51 で効いた数字：紙の玉が開く 338〜349＝玉→開きかけ→ほぼ開く の3枚を 2コマごとに大きさを替えて（150→230→330→470→900→1700px）
//   絵＝Codex で同じ玉の開き具合を3枚（緑かマゼンタの地に描いて抜く＝51/tools/key.py）
// 測る道具：mg_measure.py box <手本> f0 f1 --far <紙の色>＝紙の色から遠い一番大きい塊の外枠を毎コマ→中心と幅。同じ幅が続く所が1段
//   絵の替わり目＝段の境で SSIM が跳ぶコマ（seg_ssim.py --each で手本どうし）
import React from 'react';
import {Img, staticFile} from 'remotion';
import {rowAt} from './common';

export type CrRow = [number, string, number, number, number, number];
export const CrumpleBall: React.FC<{f: number; table: CrRow[]; f1?: number; hold?: number; wobble?: [number, number] | null; shadow?: string}> = ({f, table, f1, hold = 3, wobble = [4, 2], shadow = 'drop-shadow(0 20px 20px rgba(0,0,0,0.5))'}) => {
  const end = f1 ?? (table.length ? table[table.length - 1][0] + hold : 0);
  if (!table.length || f < table[0][0] || f >= end) return null;
  const [, src, cx, cy, w, r] = rowAt(table, f)!;
  const rot = wobble ? ((f % wobble[0]) - (wobble[0] - 1) / 2) * wobble[1] : 0;
  return <Img src={staticFile(src)} style={{position: 'absolute', left: cx - w / 2, top: cy - (w * r) / 2, width: w, height: w * r, transform: `rotate(${rot}deg)`, filter: shadow || undefined}} />;
};
