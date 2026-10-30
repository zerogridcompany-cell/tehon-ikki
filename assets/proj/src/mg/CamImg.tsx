// CamImg＝1枚の大きな絵を、手本から毎コマ測った 3x3 の鎖（カメラの動き）で動かす。51 の Mane51.tsx CamImg・Lives・RoadImg の汎用版
// 何をする：鎖の 3x3（基準のコマ k の画面 → コマ f の画面・画面の px）を CSS の matrix3d にして絵にかける。射影（3行目）もそのまま効く
//   長い横流し・振り・寄り＝「大きな1枚の絵の上をカメラが動く」作り。鏡写しで四方を広げた絵（pad）を使うと縁が出ん
// props：
//   f・src（基準のコマ k の見え方の絵＝画面と同じ大きさ）
//   chain＝cam_chain.py の出力 {"f0","f1","k","C":{"<f>":[9]}} か {"f0","M":[[9]…]}（51 の cam2.json の形）。無いコマは一番近い端のコマ
//   until（このコマで止める＝鎖が崩れる所・51 の人の列は 207 で止めた）・dx（{"<コマ>": 横の px} を足す＝51 lives_dx）
//   pad（px）・padSrc＝鏡写しで四方を pad px 広げた絵（scripts/tools/pad_mirror.py）。🔴 transformOrigin を pad px ずらして置く
//   bg＝'blur'（同じ絵を 1.3 倍・ぼかし 14px で下に敷く＝縁隠し）| 'none'・clip＝多角形（"polygon(…)"）＝手前に来る物だけ字の上に出す
//   strip＝[{src, M?: [9], mask?: CSS の mask}]＝帯（2枚目以降の見え方の絵）。M＝その絵を基準の画面へ置く 3x3（51＝inv(M[169])・左を 15px ぼかしてつなぐ）
//   whip＝{f0, f1, D, rows:[[コマ, s, L]…], left, right, Ml, Mr}＝横振り：左右の絵を D px ずらしてつないだ1枚を s だけ流す＋横だけのぶれ（σ＝L×0.29）
// 51 で効いた数字：
//   鎖のカメラ（技4）＝人の列 左へ 1674px（123→207）・分かれ道 −207px。構図を崩さず縁が出ん。🔴 カメラで縁が出る所を「真ん中から寄せて隠す」と −0.14〜−0.18（鏡写しが正）
//   振りは1枚の地図＝振りの13コマ 0.59〜0.78→0.87〜0.89（D 1036・s 164/412/624/872・L 92/124/124/92）。2枚の重ね溶け＋全方向の blur は灰色に見えた
// 測る道具：鎖＝scripts/tools/cam_chain.py <作業> f0 f1 --out x.json（LK 400点・相似・点が 10 未満のコマは止める）。🔴 カットをまたがん
//   横振り＝scripts/tools/whip_fit.py <作業> f0 f1 左 右（D・s・L）・縁＝pad_mirror.py・合っとるか＝seg_ssim.py <作業> <試し.mp4> f0 f1 --off f0
import React from 'react';
import {AbsoluteFill, Img, staticFile} from 'remotion';

export type Chain = {f0?: number; f1?: number; k?: number; C?: Record<string, number[]>; M?: number[][]};
/** 3x3（行ごと9個・2x3 の6個も可）→ CSS matrix3d（列ごと）。x'=(h0x+h1y+h2)/(h6x+h7y+h8) */
export const m3d = (h: number[]) => {
  const H = h.length === 6 ? [...h, 0, 0, 1] : h;
  return `matrix3d(${H[0]},${H[3]},0,${H[6]},${H[1]},${H[4]},0,${H[7]},0,0,1,0,${H[2]},${H[5]},0,${H[8]})`;
};
export const chainAt = (ch: Chain, f: number): number[] => {
  if (ch.C) {
    const ks = Object.keys(ch.C).map(Number).sort((a, b) => a - b);
    if (!ks.length) return [1, 0, 0, 0, 1, 0, 0, 0, 1];
    const g = Math.max(ks[0], Math.min(ks[ks.length - 1], f));
    return ch.C[String(g)] ?? ch.C[String(ks.reduce((b, x) => (Math.abs(x - g) < Math.abs(b - g) ? x : b), ks[0]))];
  }
  const M = ch.M ?? [];
  return M[Math.max(0, Math.min(M.length - 1, f - (ch.f0 ?? 0)))] ?? [1, 0, 0, 0, 1, 0, 0, 0, 1];
};
/** 3x3 の積 a·b（行ごと9個） */
export const mmul = (a: number[], b: number[]) => {
  const o: number[] = [];
  for (let r = 0; r < 3; r++) for (let c = 0; c < 3; c++) o.push(a[r * 3] * b[c] + a[r * 3 + 1] * b[3 + c] + a[r * 3 + 2] * b[6 + c]);
  return o;
};
export const shiftX = (m: number[], dx: number) => { const n = [...m]; n[2] += dx * (n[8] ?? 1); return n; };

const LAY = (W: number, H: number): React.CSSProperties => ({position: 'absolute', left: 0, top: 0, width: W, height: H, transformOrigin: '0 0'});

export const CamImg: React.FC<{f: number; src: string; chain?: Chain; until?: number; dx?: Record<string, number>; pad?: number; padSrc?: string; bg?: 'blur' | 'none'; clip?: string; W?: number; H?: number;
  strip?: {src: string; M?: number[]; mask?: string; op?: number}[];
  whip?: {f0: number; f1: number; D: number; rows: [number, number, number][]; left: string; right: string; Ml?: number[]; Mr?: number[]}}> = (P) => {
  const W = P.W ?? 1920, H = P.H ?? 1080;
  const {f} = P;
  const wh = P.whip;
  if (wh && f >= wh.f0 && f < wh.f1) {
    const row = [...wh.rows].filter((r) => f >= r[0]).pop() ?? wh.rows[0];
    const [, s, L] = row;
    const id = `whip${f}`;
    return (
      <AbsoluteFill>
        <svg width={0} height={0} style={{position: 'absolute'}}><filter id={id} x="-0.2" width="1.4" colorInterpolationFilters="sRGB"><feGaussianBlur stdDeviation={`${(L * 0.29).toFixed(1)} 0`} edgeMode="duplicate" /></filter></svg>
        <div style={{position: 'absolute', inset: 0, filter: `url(#${id})`}}>
          <Img src={staticFile(wh.left)} style={{...LAY(W, H), transform: m3d(shiftX(wh.Ml ?? [1, 0, 0, 0, 1, 0, 0, 0, 1], -s))}} />
          <Img src={staticFile(wh.right)} style={{...LAY(W, H), transform: m3d(shiftX(wh.Mr ?? [1, 0, 0, 0, 1, 0, 0, 0, 1], wh.D - s))}} />
        </div>
      </AbsoluteFill>
    );
  }
  const ff = P.until != null ? Math.min(f, P.until) : f;
  let M = P.chain ? chainAt(P.chain, ff) : [1, 0, 0, 0, 1, 0, 0, 0, 1];
  const ddx = P.dx?.[String(f)]; if (ddx) M = shiftX(M, ddx);
  const t = m3d(M);
  const pad = P.pad ?? 0;
  return (
    <AbsoluteFill>
      {!P.clip && (P.bg ?? 'blur') === 'blur' && <Img src={staticFile(P.src)} style={{position: 'absolute', inset: 0, width: W, height: H, transform: 'scale(1.3)', filter: 'blur(14px)'}} />}
      <div style={{...LAY(W, H), transform: t, clipPath: P.clip}}>
        {pad && P.padSrc
          ? <Img src={staticFile(P.padSrc)} style={{position: 'absolute', left: -pad, top: -pad, width: W + 2 * pad, height: H + 2 * pad}} />
          : <Img src={staticFile(P.src)} style={LAY(W, H)} />}
        {P.strip?.map((s, i) => <Img key={i} src={staticFile(s.src)} style={{...LAY(W, H), transform: s.M ? m3d(s.M) : undefined, opacity: s.op ?? 1, WebkitMaskImage: s.mask, maskImage: s.mask}} />)}
      </div>
    </AbsoluteFill>
  );
};
