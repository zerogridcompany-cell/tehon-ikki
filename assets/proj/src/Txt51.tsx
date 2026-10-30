import React from 'react';
import {AbsoluteFill, continueRender, delayRender, getInputProps, random, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';

// 字を1つずつ Remotion（SVG）で描く部品。51 の proj/src/parts/Txt.tsx の汎用版（10/25）。PIL/ffmpeg で焼かん。
// 値は scripts/tools/txt51/ の道具が字の表（texts.json）に書く。名前の一覧は txt51/README.md の「Remotion 側で読む値」。
// 使い方：
//   import TEXTS from './texts.json';
//   import {loadTxtFonts, TxtLayer, TxtSheet} from './Txt51';
//   loadTxtFonts({serif: {file: 'fonts/InstrumentSerif-Regular.ttf'}, sans: {file: 'fonts/Inter[opsz,wght].ttf', weight: '100 900', opsz: 32, xh: 0.516}});
//   <TxtLayer texts={TEXTS as any} />                       … 本編（今のコマに出とる字を全部）
//   <Composition id="TxtSheet" component={() => <TxtSheet texts={TEXTS as any} />} durationInFrames={TEXTS.length} .../>
//     … 字だけの層（コマ k＝k 番目の字を測るコマで・透明の地）。書き出し：npx remotion render src/index.ts TxtSheet <作業>/txt51/sheet --sequence --image-format=png
// 試しの props（全部の字か id ごとに・"*"＝全部）：{"wd":{"*":-50}}＝太さ・{"dk":{"*":0.88}}＝下の出・{"ka":{"*":0.92}}＝上の出・{"eb":1.4}＝縁のぼけ

export type FontDef = {file: string; weight?: string; style?: string; opsz?: number; xh?: number; italicKey?: string};
const FONTS: Record<string, FontDef> = {};
export const fam = (key: string) => `Txt51_${key}`;
/** 書体を FontFace で読む（読み終わるまで delayRender で待つ＝読む前は別の書体で描かれる）。モジュールの頭で1回呼ぶ */
export const loadTxtFonts = (defs: Record<string, FontDef>) => {
  Object.assign(FONTS, defs);
  const h = delayRender('Txt51 fonts');
  Promise.all(Object.entries(defs).map(([k, d]) => new FontFace(fam(k), `url(${staticFile(d.file)})`, {weight: d.weight ?? '400', style: d.style ?? 'normal'}).load()))
    .then((fs) => { fs.forEach((f) => (document.fonts as any).add(f)); continueRender(h); })
    .catch(() => continueRender(h));
};

const P = ((getInputProps() as any) || {}) as any;
const pick = (m: Record<string, number> | undefined, d: any, v: number | undefined, def: number) => (m && (m[d.id] ?? m['*'])) ?? v ?? def;

export type T = {
  id: string; text: string; font: string; w: number; color: string; t0: number; t1: number;
  reveal?: [number, number] | null; words?: [number, number, number, number][]; rtl?: number; cfade?: number; cdx?: number[];
  exit?: string; xout?: [number, number] | null; fs: number; sx: number; sy?: number; x: number; y: number;
  wv?: number; dk?: number; ka?: number; sw?: number; er?: number; eb?: number; mul?: string; blend?: string; italicTail?: number;
  glow?: number; shc?: [number, number]; opacity?: number; fadein?: number; blurin?: number; blurout?: [number, number, number];
  blurk?: [number, number][]; blurgain?: [number, number][]; erop?: [number, number][]; dyk?: [number, number][];
  jumps?: [number, number, number][]; clipY?: number; zoom?: [number, number, number]; zoomk?: [number, number][]; zc?: [number, number];
  qbox?: [number, number]; qk?: number[][]; qrect?: [number, number, number, number]; qcolor?: string;
};
const cl = (v: number) => Math.max(0, Math.min(1, v));
const lerpTab = (k: number[][], x: number, col = 1) => {
  if (x <= k[0][0]) return k[0][col];
  for (let i = 1; i < k.length; i++) if (x < k[i][0]) return k[i - 1][col] + (k[i][col] - k[i - 1][col]) * cl((x - k[i - 1][0]) / (k[i][0] - k[i - 1][0]));
  return k[k.length - 1][col];
};
const stepTab = (k: number[][], x: number) => { const r = [...k].reverse().find((e) => x >= e[0]); return r ? r[1] : k[0][1]; };

/** 1字の濃さ：words＝[字の始め, 終わり, 秒の始め, 終わり]（語ごとに打つ）・reveal＝[r0,r1]（1字ずつ等間隔・rtl で右から）。1字の溶けは cfade 秒（既定 0.1＝手本の打ち字は 3コマ） */
export const charAlpha = (d: T, i: number, n: number, t: number) => {
  const FADE = d.cfade ?? 0.1;
  if (d.words) {
    for (const [a, b, s, e] of d.words) if (i >= a && i < b) return cl((t - (s + ((e - s) * (i - a)) / Math.max(1, b - a - 1))) / FADE);
    return 1;
  }
  if (!d.reveal) return 1;
  const [r0, r1] = d.reveal;
  const k = d.rtl ? n - 1 - i : i;
  return cl((t - (r0 + ((r1 - r0) * k) / Math.max(1, n - 1))) / FADE + 1.0);
};

/** 測るコマ（出揃ってから消えるまでの真ん中）＝ txt51/_t51.py の frame_of と同じ */
export const sheetFrame = (d: any, fps: number) => { const a = Math.max(d.t0, (d.reveal || [0, 0])[1]); return Math.round((fps * (a + d.t1)) / 2); };

export const Txt: React.FC<{d: T; t: number; fps: number; W: number; H: number}> = ({d, t, fps, W, H}) => {
  const q0 = d.qbox ? d.qbox[0] : d.t0;
  if (t < Math.min(d.t0, q0) || t >= d.t1) return null;
  const fr = t * fps;
  const fd = FONTS[d.font] || ({} as FontDef);
  const ff = fam(d.font);
  let op = d.opacity ?? 1;
  if (d.fadein) op *= cl((t - d.t0) / d.fadein);
  let blur = d.blurin ? (1 - cl((t - d.t0) / (d.fadein || 0.3))) * 14 : 0;
  if (d.blurk) blur = stepTab(d.blurk, fr + 0.01);   // 手本から測ったぼけの段（コマ, σpx）＝blur_track.py
  if (d.blurout && t > d.blurout[0]) blur += cl((t - d.blurout[0]) / (d.blurout[1] - d.blurout[0])) * d.blurout[2];
  let clip: string | undefined;
  const glitch = d.exit === 'glitch' && d.xout && t >= d.xout[0];
  if (d.xout && t >= d.xout[0]) {
    const p = cl((t - d.xout[0]) / (d.xout[1] - d.xout[0]));
    if (d.exit === 'fade') op *= 1 - p;
    if (d.exit === 'wipe') clip = `inset(0 0 0 ${p * 100}%)`;
    if (d.exit === 'glitch') op *= 1 - p * p;
  }
  let jy = 0;   // jumps＝[秒, 縦のずれ px, 濃さ]（段で跳ぶ消え方）・clipY より下は見せん
  if (d.jumps && t >= d.jumps[0][0]) {
    const j = [...d.jumps].reverse().find((x) => t >= x[0])!;
    jy = j[1]; op *= j[2];
    if (d.clipY) clip = `inset(0 0 ${H - d.clipY}px 0)`;
  }
  if (d.dyk) jy += lerpTab(d.dyk, t);   // 字が流れる（秒, 縦のずれ px）
  let tr = `translate(${d.x},${d.y + jy}) scale(${d.sx},${d.sy ?? 1})`;
  const [zx, zy] = d.zc ?? [W / 2, H / 2];
  if (d.zoom) {
    const [z0, z1, zk] = d.zoom; const p = cl((t - z0) / (z1 - z0)); const e = p * p * (3 - 2 * p); const s = 1 + (zk - 1) * e;
    tr = `translate(${zx},${zy}) scale(${s}) translate(${-zx},${-zy}) ` + tr;
  }
  if (d.zoomk) { const s = lerpTab(d.zoomk, t); tr = `translate(${zx},${zy}) scale(${s}) translate(${-zx},${-zy}) ` + tr; }
  const chars = [...d.text];
  const n = chars.length;
  const wt = (d.wv ?? d.w) + pick(P.wd, d, 0, 0);
  const dk = pick(P.dk, d, d.dk, 1);
  const ka = pick(P.ka, d, d.ka, 1);
  const fill = d.mul ?? d.color;
  const fvs = fd.opsz ? `'opsz' ${fd.opsz}, 'wght' ${wt}` : `'wght' ${wt}`;
  const mk = (trx: string, cp?: string) => (
    <text transform={trx} clipPath={cp} fontSize={d.fs} fontFamily={ff} fontWeight={wt} fontStyle={fd.style ?? 'normal'} fill={fill}
      stroke={d.sw ? fill : undefined} strokeWidth={d.sw || undefined} strokeLinejoin="round" style={{fontVariationSettings: fvs}}>
      {chars.map((c, i) => {
        const it = d.italicTail && i >= n - d.italicTail;
        const a = charAlpha(d, i, n, t);
        return (
          <tspan key={i} dx={d.cdx ? d.cdx[i] : undefined} fillOpacity={a} strokeOpacity={d.sw ? a : undefined}
            fontFamily={it && fd.italicKey ? fam(fd.italicKey) : undefined} fontStyle={it ? 'italic' : undefined}>
            {c}
          </tspan>
        );
      })}
    </text>
  );
  // 下の出（dk）・上の出（ka）の縮め：ベースラインより下は縦に dk 倍・x の高さ（xh em）より上は縦に ka 倍。間はそのまま
  const xh = (fd.xh ?? 0.516) * d.fs;
  const body0 = dk !== 1 || ka !== 1 ? (
    <>
      <defs>
        <clipPath id={`dkt_${d.id}`} clipPathUnits="userSpaceOnUse"><rect x={-20000} y={-20000} width={40000} height={20000 - xh + 0.6} /></clipPath>
        <clipPath id={`dku_${d.id}`} clipPathUnits="userSpaceOnUse"><rect x={-20000} y={ka !== 1 ? -xh : -20000} width={40000} height={ka !== 1 ? xh + 0.6 : 20000.6} /></clipPath>
        <clipPath id={`dkd_${d.id}`} clipPathUnits="userSpaceOnUse"><rect x={-20000} y={0} width={40000} height={20000} /></clipPath>
      </defs>
      {ka !== 1 && mk(`${tr} translate(0,${-xh}) scale(1,${ka}) translate(0,${xh})`, `url(#dkt_${d.id})`)}
      {mk(tr, `url(#dku_${d.id})`)}
      {mk(`${tr} scale(1,${dk})`, `url(#dkd_${d.id})`)}
    </>
  ) : mk(tr);
  // er＝線だけ削る（feMorphology erode・px）＝太さ wv を変えると字の幅も変わるので、幅を保ったまま細らせる
  const body = d.er ? <><defs><filter id={`er_${d.id}`} x="0" y="0" width={W} height={H} filterUnits="userSpaceOnUse"><feMorphology operator="erode" radius={d.er} /></filter></defs><g filter={`url(#er_${d.id})`}>{body0}</g></> : body0;
  const eb = d.eb ?? P.eb ?? 0;   // 縁のぼけ（手本の圧縮のにじみ）
  if (eb) blur = Math.sqrt(blur * blur + eb * eb);
  const flt = [d.glow ? 'drop-shadow(0 0 18px rgba(255,255,255,0.95)) drop-shadow(0 0 60px rgba(200,240,255,0.8))' : '', blur > 0.3 || eb ? `blur(${blur}px)` : ''].join(' ').trim();
  const mix = (d.blend as any) || (d.mul ? 'multiply' : undefined);
  if (glitch) {   // 横の帯6本を種つき乱数でずらす（3コマごと＝10fps の段）
    const step = Math.floor(t * 10);
    return (
      <>
        {[0, 1, 2, 3, 4, 5].map((b) => {
          const y0 = d.y - d.fs * 0.8 + (b * d.fs) / 6;
          const dx = (random(`g${d.id}${b}${step}`) - 0.5) * 80 * (H / 1080);
          const show = random(`h${d.id}${b}${step}`) > 0.25;
          return (
            <svg key={b} width={W} height={H} style={{position: 'absolute', inset: 0, opacity: show ? op : 0, clipPath: `inset(${y0}px 0 ${H - y0 - d.fs / 6}px 0)`, transform: `translateX(${dx}px)`}}>
              {body}
            </svg>
          );
        })}
      </>
    );
  }
  // 光の筋：字を光の中心から少しずつ大きくした写しを薄く重ねる（中心は毎コマ少し動く）
  const [scx, scy] = d.shc ?? [W / 2 + 20, H / 2];
  const shine = d.glow ? (
    <svg width={W} height={H} style={{position: 'absolute', inset: 0, opacity: op, mixBlendMode: 'screen', filter: 'blur(5px)'}}>
      {Array.from({length: 26}).map((_, k) => {
        const cx = scx + Math.sin(t * 3) * 120, sc = 1 + 0.035 * (k + 1);
        return <g key={k} transform={`translate(${cx},${scy}) scale(${sc},${sc}) translate(${-cx},${-scy})`} opacity={0.13 * (1 - k / 26)}><text transform={tr} fontSize={d.fs} fontFamily={ff} fontWeight={wt} fill="#ffffff">{d.text}</text></g>;
      })}
    </svg>
  ) : null;
  const ep = d.erop ? Math.max(0, lerpTab(d.erop, fr)) : 0;   // 溶けて削れる消え方の進み（コマ, 0→1）＝ero_fit.py
  const gain = d.blurgain ? stepTab(d.blurgain, fr + 0.01) : 1;   // ぼけとる間の明るさ（同じ層を重ねる）
  const extra = gain > 1 ? Array.from({length: Math.ceil(gain - 1)}, (_, j) => Math.min(1, gain - 1 - j)) : [];
  // 字の後ろの箱（qrect＝[x,y,幅,高さ]）：qbox＝[秒の始め, 終わり] で左から伸びる／qk＝[[コマ, 左, 右], …] の測った表
  const qr = d.qrect;
  const qbox = qr && (d.qk ? (() => {
    const k = d.qk!; if (fr < k[0][0]) return null;
    const L = lerpTab(k, fr, 1), R = lerpTab(k, fr, 2);
    return <rect x={L} y={qr[1]} width={R - L} height={qr[3]} fill={d.qcolor ?? '#ffffff'} />;
  })() : d.qbox ? <rect x={qr[0]} y={qr[1]} width={qr[2] * cl((t - d.qbox[0]) / (d.qbox[1] - d.qbox[0]))} height={qr[3]} fill={d.qcolor ?? '#ffffff'} /> : null);
  const sty = {position: 'absolute' as const, inset: 0, filter: flt || undefined, clipPath: clip, mixBlendMode: mix};
  return (
    <>
      {shine}
      {extra.map((eo, j) => <svg key={`g${j}`} width={W} height={H} style={{...sty, opacity: op * eo}}>{body}</svg>)}
      <svg width={W} height={H} style={{...sty, opacity: op}}>
        {qbox}
        {ep > 0 ? (
          <>
            <defs>
              {/* 溶けて斑に削れる：雑音のしきい値で削る＋雑音でゆらす＋縁を少し長く残す。ero_fit.py の較正の表はこのフィルタで測った物＝数字を変えたら較正し直す */}
              <filter id={`ero_${d.id}`} filterUnits="userSpaceOnUse" x={0} y={0} width={W} height={H}>
                <feTurbulence type="turbulence" baseFrequency="0.03 0.045" numOctaves={3} seed={11} result="n" />
                <feDisplacementMap in="SourceGraphic" in2="n" scale={40 * ep} xChannelSelector="R" yChannelSelector="G" result="dd" />
                <feColorMatrix in="n" type="matrix" values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 0" result="na0" />
                <feMorphology in="SourceAlpha" operator="erode" radius={5} result="er" />
                <feComposite in="SourceAlpha" in2="er" operator="arithmetic" k1={0} k2={1} k3={-1} k4={0} result="edge" />
                <feComposite in="na0" in2="edge" operator="arithmetic" k1={0} k2={1} k3={0.15} k4={0} result="na" />
                <feComponentTransfer in="na" result="m"><feFuncA type="linear" slope={12} intercept={-12 * (0.02 + 0.6 * ep)} /></feComponentTransfer>
                <feComposite in="dd" in2="m" operator="in" />
              </filter>
            </defs>
            <g filter={`url(#ero_${d.id})`}>{body}</g>
          </>
        ) : body}
      </svg>
    </>
  );
};

/** 本編：今のコマに出とる字を全部描く。only＝この id だけ（くっきりの字を全画面のぼかしの外に出す時など） */
export const TxtLayer: React.FC<{texts: T[]; only?: (d: T) => boolean; frame?: number}> = ({texts, only, frame}) => {
  const f0 = useCurrentFrame(); const {fps, width, height} = useVideoConfig();
  const t = (frame ?? f0) / fps;
  return <>{texts.filter((d) => !only || only(d)).map((d) => <Txt key={d.id} d={d} t={t} fps={fps} W={width} H={height} />)}</>;
};

/** 字だけの層（透明の地）。コマ k＝k 番目の字を測るコマ（sheetFrame）で描く。後ろの箱・光の筋・重ね方・濃さ・ぼけは外す＝字の形だけ（txt_reg・glyph_match の型） */
export const TxtSheet: React.FC<{texts: T[]}> = ({texts}) => {
  const k = useCurrentFrame(); const {fps, width, height} = useVideoConfig();
  const d0 = texts[k] as any;
  if (!d0) return null;
  const {qbox, qk, qrect, glow, blend, opacity, blurin, fadein, blurout, blurk, blurgain, erop, dyk, eb, ...rest} = d0;
  const d = {...rest, eb: 0} as T;
  return <AbsoluteFill><Txt d={d} t={sheetFrame(d0, fps) / fps} fps={fps} W={width} H={height} /></AbsoluteFill>;
};
