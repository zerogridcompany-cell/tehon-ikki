// Swap＝2〜3コマごとの差し替えの表（絵・箱・回り）。51 の Extra.tsx Eyes・IntroNotes と Scenes.tsx PaypalScene と Mane51.tsx の seq/seqfade の汎用版
// 何をする：table の行（[コマ, 絵, 箱?, 回り?]）を越えるたびに絵を替える。箱が無ければ全画面。滑らかにせず段で替える（手作りの紙・連打の味）
// props：
//   f・table＝[[コマ, 絵, [x0,y0,x1,y1]?, 度?]…]（コマの小さい順）・f1（ここで消える・含まん）
//   fit('cover'|'fill'|'contain')・filter・shadow（boxShadow）
//   zoom＝コマごとの寄り（1行の中で 1+zoom·(f−行のコマ)）。51＝鴨・ひまわり・子猫・札の連打 0.012（2556〜）・ひよこ・猿は 0（寄らん）
//   fade＝[[コマ, 濃さ]…]（seqfade）＝最後の絵（table の最後）を下に敷き、今の絵をその濃さで重ねる＝数コマかけて薄れて次へ
// 51 で効いた数字：
//   頭の紙幣のコラージュ（36〜95）を 30fps で測り直した＝3コマごと（36,39,42,49,51…）・17枚＝波 +0.004・1秒 SSIM 0.585→0.613（10fps の帯から作った表は間隔を間違えた）
//   PayPal＝2107 から 2・2・3・3・2・2・2・2・3 コマで3枚を回す・鎖の薄れ（seqfade）＝濃さ 13コマで手本と ±1.5 以内
//   🔴 連打の場面で毎コマ寄せると ffmpeg のカット判定が消える（v7 でカット 88→66）＝手本の合間の差（0.0〜0.4 なら止まっとる）を先に測ってから zoom を付ける
// 測る道具：替わるコマ＝mg_measure.py steps <手本> f0 f1 [--box …]（前のコマとの差が跳ぶコマ＝替わり・0 のコマ＝止め）
//   箱＝mg_measure.py box <手本> f0 f1 --far <地の色>（地の色から遠い一番大きい塊の外枠）・どの絵か＝コマを目で読む（同じ絵の繰り返しを見つける）
import React from 'react';
import {Img, staticFile, useVideoConfig} from 'remotion';
import {rowAt, stepAt} from './common';

export type SwapRow = [number, string, number[]?, number?];
export const Swap: React.FC<{f: number; table: SwapRow[]; f1?: number; fit?: string; filter?: string; shadow?: string; zoom?: number; fade?: [number, number][]}> = ({f, table, f1, fit = 'cover', filter, shadow, zoom = 0, fade}) => {
  const {width: W, height: H} = useVideoConfig();
  if (f1 != null && f >= f1) return null;
  const r = rowAt(table, f); if (!r) return null;
  const [k, src, box, rot] = r;
  const place = (s: string, op = 1, z = 1) => {
    const [x0, y0, x1, y1] = box && box.length === 4 ? box : [0, 0, W, H];
    return <Img src={staticFile(s)} style={{position: 'absolute', left: x0, top: y0, width: x1 - x0, height: y1 - y0, objectFit: fit as any, opacity: op,
      transform: `${rot ? `rotate(${rot}deg) ` : ''}${z !== 1 ? `scale(${z})` : ''}` || undefined, filter, boxShadow: shadow}} />;
  };
  const z = 1 + zoom * (f - k);
  const last = table[table.length - 1][1];
  const op = fade ? stepAt(fade, f) : undefined;
  if (fade && op != null && src !== last) return <>{place(last)}{place(src, op, z)}</>;
  return place(src, 1, z);
};
