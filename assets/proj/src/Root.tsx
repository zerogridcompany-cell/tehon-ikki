import React from 'react';
import {Composition} from 'remotion';
import {Main} from './Main';
import {TxtSheet} from './Txt51';
import CFG from './cfg.json';
import TEXTS from './texts.json';
// cfg.json＝init で手本から書く（frames・fps・width・height）
const SheetComp: React.FC = () => <TxtSheet texts={TEXTS as any} />;
export const RemotionRoot: React.FC = () => (
  <>
    <Composition id="Main" component={Main} durationInFrames={(CFG as any).frames} fps={(CFG as any).fps} width={(CFG as any).width} height={(CFG as any).height} />
    {/* 字だけの層（txt51 の道具が測る用）＝1コマ1字・README「字の表を変えたら毎回」 */}
    <Composition id="TxtSheet" component={SheetComp} durationInFrames={Math.max(1, (TEXTS as any[]).length)} fps={(CFG as any).fps} width={(CFG as any).width} height={(CFG as any).height} />
  </>
);
