// waza3d 共通：曲線・時間・字体（mg-mane easing.md の役の表どおり）
import {Easing, interpolate} from 'remotion';
import {loadFont as loadInter} from '@remotion/google-fonts/Inter';
const _inter = loadInter('normal', {weights: ['400', '500', '600', '700'], subsets: ['latin']});
export const INTER = _inter.fontFamily;
export const interReady = _inter.waitUntilDone;
export const FONT = `${INTER}, -apple-system, Helvetica, Arial, sans-serif`;
// 日本語は Mac の Hiragino を先に（Google の JP は 363 回読みに行って重い）
export const FONT_JP = `${INTER}, 'Hiragino Sans', 'Hiragino Kaku Gothic ProN', 'Noto Sans JP', sans-serif`;

export const clamp01 = (x: number) => Math.min(1, Math.max(0, x));
// 役 → 曲線（easing.md）
export const E = {
  out: Easing.bezier(0.16, 1, 0.3, 1), // 出てくる＝最初速く後ゆっくり
  in: Easing.bezier(0.7, 0, 0.84, 0), // 消える
  inout: Easing.bezier(0.65, 0, 0.35, 1), // 中を移動
  apple: Easing.bezier(0.45, 0, 0.12, 1), // 加速短く(約 0.3)・減速長く(約 0.7)＝Apple の寄り
  settle: Easing.bezier(0.1848, 0.3986, 0.3491, 1.2043), // compreel の共通の落ち着き（軽い行き過ぎ）
  linear: (t: number) => t,
};
// f が a→b の間で 0→1（曲線つき・外は止める）
export const tw = (f: number, a: number, b: number, e: (t: number) => number = E.inout) =>
  e(clamp01((f - a) / (b - a)));
export const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
// 対数空間の補間（寄り・引きを均等に見せる）
export const logLerp = (a: number, b: number, t: number) => Math.exp(Math.log(a) + (Math.log(b) - Math.log(a)) * t);
// 止まり 0 のための「息」：ゆっくりした連続のゆれ（0 で止めない）
export const breathe = (f: number, amp: number, period = 90, phase = 0) => Math.sin((f / period) * Math.PI * 2 + phase) * amp;
export {interpolate};
// 粒（帯消し・地の下に敷く）
export const GRAIN = `url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='240' height='240'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='2' stitchTiles='stitch'/><feColorMatrix values='0 0 0 0 .5  0 0 0 0 .5  0 0 0 0 .5  0 0 0 .9 0'/></filter><rect width='100%' height='100%' filter='url(%23n)'/></svg>")`;
