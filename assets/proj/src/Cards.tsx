import React from 'react';
import {useCurrentFrame} from 'remotion';
// 字・光・札など、手本ごとに形が違うカード。測り方と型は Cards.example.tsx（r2 の実物）と references/waza.md「カード」を見る
type Card = {f0: number; f1: number; el: React.ReactNode};
const CARDS: Card[] = [];
export const Cards: React.FC = () => {
  const f = useCurrentFrame();
  const c = CARDS.find((c) => f >= c.f0 && f <= c.f1);
  return c ? <>{c.el}</> : null;
};
