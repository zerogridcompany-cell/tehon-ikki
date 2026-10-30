import React from 'react';
import {AbsoluteFill, Img, staticFile, useCurrentFrame} from 'remotion';
import FLASH from './flash.json';

// 白く光る1コマ（手本は字幕も無い真っ白な反転の絵）：全部の層の上に1枚だけ被せる。絵は tmp/flash_make.py が手本と比べて選んだ物
type F = {f: number; src?: string; op?: number; wash?: number[]; text?: {s: string; x: number; y: number; fs: number; fill: string}};
export const Flash: React.FC = () => {
  const f = useCurrentFrame();
  const h = (FLASH as F[]).find((x) => x.f === f);
  if (!h) return null;
  // wash＝白い光の差し込み（左の濃さ・右の濃さ。手本の明るさから列ごとに当てた1次の傾き）
  if (h.wash) {
    const [l, r] = h.wash.map((v) => Math.max(0, Math.min(1, v)));
    return <AbsoluteFill style={{background: `linear-gradient(to right, rgba(255,255,255,${l}), rgba(255,255,255,${r}))`}} />;
  }
  // text＝黒地の大きな字（72 の「NO」：字の中の元の映像は未発見＝手本の字の中の平均の色で塗る）
  if (h.text) {
    const t = h.text;
    return (
      <AbsoluteFill style={{backgroundColor: '#000'}}>
        <style>{`@font-face{font-family:'R2TNRB';src:url('${staticFile('fonts/TNRBold.ttf')}');}`}</style>
        <svg width={1280} height={720}><text x={t.x} y={t.y} fill={t.fill} style={{fontFamily: 'R2TNRB', fontSize: t.fs}}>{t.s}</text></svg>
      </AbsoluteFill>
    );
  }
  return <AbsoluteFill><Img src={staticFile(h.src!)} style={{width: 1280, height: 720, opacity: h.op ?? 1}} /></AbsoluteFill>;
};
